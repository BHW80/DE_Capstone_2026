-- ==============================================================================
-- YouTube DataOps Platform (2026 Edition) - Release v2.3.0
-- Multi-Source Enterprise Extension: MariaDB CRM Creator Contracts
-- Host: 127.0.0.1 / Socket: /tmp/mariadb.sock
-- Database: usrdb_welbmqup
-- ==============================================================================

USE usrdb_welbmqup;

-- 1. Tabelle anlegen (falls noch nicht vorhanden)
CREATE TABLE IF NOT EXISTS creator_contracts (
    contract_id INT AUTO_INCREMENT PRIMARY KEY,
    channel_title VARCHAR(150) NOT NULL UNIQUE,
    partner_tier VARCHAR(50) NOT NULL DEFAULT 'Standard',
    revenue_share_pct DECIMAL(4,2) NOT NULL DEFAULT 0.55,
    country_code VARCHAR(3) NOT NULL DEFAULT 'USA',
    account_manager VARCHAR(100) NOT NULL,
    contract_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    signed_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_channel (channel_title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Synthetische Verträge für Kanäle unseres YouTube-Datensatzes einfügen
INSERT INTO creator_contracts (channel_title, partner_tier, revenue_share_pct, country_code, account_manager, contract_status, signed_date)
VALUES
    ('CaseyNeistat', 'Enterprise', 0.80, 'USA', 'Sarah Steiner', 'ACTIVE', '2016-01-15'),
    ('LastWeekTonight', 'Enterprise', 0.85, 'USA', 'Michael Brandstetter', 'ACTIVE', '2015-04-10'),
    ('Rudy Mancuso', 'Partner', 0.70, 'USA', 'Sarah Steiner', 'ACTIVE', '2016-09-01'),
    ('Good Mythical Morning', 'Enterprise', 0.75, 'USA', 'David Koch', 'ACTIVE', '2014-03-20'),
    ('nigahiga', 'Enterprise', 0.80, 'USA', 'Sarah Steiner', 'ACTIVE', '2013-11-05'),
    ('iJustine', 'Partner', 0.70, 'USA', 'Elena Weber', 'ACTIVE', '2015-08-12'),
    ('Saturday Night Live', 'Enterprise', 0.85, 'USA', 'Michael Brandstetter', 'ACTIVE', '2012-09-18'),
    ('CrazyRussianHacker', 'Partner', 0.65, 'USA', 'David Koch', 'ACTIVE', '2016-06-30'),
    ('20th Century Fox', 'Enterprise', 0.90, 'USA', 'Michael Brandstetter', 'ACTIVE', '2011-01-01'),
    ('Vox', 'Enterprise', 0.75, 'USA', 'Elena Weber', 'ACTIVE', '2015-05-14'),
    ('NFL', 'Enterprise', 0.90, 'USA', 'Michael Brandstetter', 'ACTIVE', '2014-08-01'),
    ('amc', 'Enterprise', 0.85, 'USA', 'Michael Brandstetter', 'ACTIVE', '2013-10-15'),
    ('marshmello', 'Enterprise', 0.80, 'USA', 'Sarah Steiner', 'ACTIVE', '2017-02-10'),
    ('NowThis World', 'Standard', 0.55, 'USA', 'David Koch', 'ACTIVE', '2017-01-11'),
    ('The king of DIY', 'Standard', 0.55, 'CAN', 'David Koch', 'ACTIVE', '2016-12-05'),
    ('BostonDynamics', 'Enterprise', 0.70, 'USA', 'Elena Weber', 'ACTIVE', '2015-03-22'),
    ('Cracked', 'Partner', 0.65, 'USA', 'David Koch', 'ACTIVE', '2014-11-19'),
    ('TED-Ed', 'Enterprise', 0.80, 'USA', 'Elena Weber', 'ACTIVE', '2013-06-01'),
    ('PeterSripol', 'Standard', 0.60, 'USA', 'David Koch', 'ACTIVE', '2017-04-18'),
    ('SciShow', 'Partner', 0.70, 'USA', 'Elena Weber', 'ACTIVE', '2014-02-28'),
    ('Life Noggin', 'Standard', 0.60, 'USA', 'David Koch', 'ACTIVE', '2016-07-07'),
    ('Tested', 'Partner', 0.70, 'USA', 'Elena Weber', 'ACTIVE', '2015-10-12'),
    ('Tom Scott', 'Enterprise', 0.75, 'GBR', 'Sarah Steiner', 'ACTIVE', '2015-01-20'),
    ('Refinery29', 'Partner', 0.65, 'USA', 'Elena Weber', 'ACTIVE', '2016-05-09')
ON DUPLICATE KEY UPDATE
    partner_tier = VALUES(partner_tier),
    revenue_share_pct = VALUES(revenue_share_pct),
    account_manager = VALUES(account_manager);
