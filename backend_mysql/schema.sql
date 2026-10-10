-- AegisShield MySQL schema (tables are also auto-created on first server start)
CREATE DATABASE IF NOT EXISTS aegisshield CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE aegisshield;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'user',
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS scans (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  type VARCHAR(10) NOT NULL,
  input TEXT NOT NULL,
  score INT NOT NULL,
  level VARCHAR(20) NOT NULL,
  verdict VARCHAR(80) NOT NULL,
  result JSON NOT NULL,
  created_at DATETIME NOT NULL,
  INDEX ix_scans_user_id (user_id),
  INDEX ix_scans_created_at (created_at),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS safe_sites (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  domain VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uq_safe_site (user_id, domain),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS login_attempts (
  identifier VARCHAR(300) PRIMARY KEY,
  count INT NOT NULL DEFAULT 0,
  last DATETIME NOT NULL
);
