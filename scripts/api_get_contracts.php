<?php
/**
 * YouTube DataOps Platform (2026 Edition) - Release v2.3.0
 * Secure REST-API Exporter for MariaDB CRM Creator Contracts
 * Endpoint: https://www.weltler.at/api/get_contracts.php
 */

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');

// 1. Konfiguration
$DB_USER   = 'welbmqup';
$DB_PASS   = 'DEIN_MARIADB_PASSWORT'; // Bitte hier dein Passwort eintragen
$DB_NAME   = 'usrdb_welbmqup';
$API_TOKEN = 'de_capstone_2026_secret_token'; // Sicherheits-Token für die Pipeline

// 2. Sicherheits-Check (Bearer Token Authentication)
$headers = getallheaders();
$authHeader = isset($headers['Authorization']) ? $headers['Authorization'] : '';

if (!$authHeader && isset($_SERVER['HTTP_AUTHORIZATION'])) {
    $authHeader = $_SERVER['HTTP_AUTHORIZATION'];
}

$expectedHeader = 'Bearer ' . $API_TOKEN;
if (trim($authHeader) !== $expectedHeader) {
    http_response_code(401);
    echo json_encode([
        'status' => 'error',
        'message' => 'Unauthorized: Ungueltiger oder fehlender Bearer Token.'
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

// 3. Datenbankverbindung herstellen (bevorzugt ueber /tmp/mariadb.sock, Fallback 127.0.0.1)
try {
    if (file_exists('/tmp/mariadb.sock')) {
        $dsn = "mysql:unix_socket=/tmp/mariadb.sock;dbname=$DB_NAME;charset=utf8mb4";
    } else {
        $dsn = "mysql:host=127.0.0.1;port=3306;dbname=$DB_NAME;charset=utf8mb4";
    }

    $pdo = new PDO($dsn, $DB_USER, $DB_PASS, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);

    // 4. Daten abfragen
    $stmt = $pdo->query("SELECT contract_id, channel_title, partner_tier, revenue_share_pct, country_code, account_manager, contract_status, signed_date, created_at FROM creator_contracts ORDER BY contract_id ASC");
    $contracts = $stmt->fetchAll();

    // 5. JSON Antwort liefern
    echo json_encode([
        'status'    => 'success',
        'source'    => 'MariaDB@www.weltler.at (usrdb_welbmqup)',
        'extracted_at' => gmdate('Y-m-d\TH:i:s\Z'),
        'count'     => count($contracts),
        'data'      => $contracts
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'status'  => 'error',
        'message' => 'Datenbankfehler: ' . $e->getMessage()
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}
