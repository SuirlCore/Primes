-- ------------------------
-- create database---------
-- ------------------------

DROP DATABASE IF EXISTS primes;

CREATE DATABASE primes;

USE primes;

-- ------------------------
-- tables------------------
-- ------------------------

CREATE TABLE IF NOT EXISTS primes (
	primeID int NOT NULL AUTO_INCREMENT,
  	primeNum int NOT NULL,
    PRIMARY KEY (primeID)
);

CREATE TABLE IF NOT EXISTS multiPrimes (
	multiPrimeID int NOT NULL AUTO_INCREMENT,
	userID char(30),
  	primeIndex int,
	multiPrimeNum int NOT NULL,
    PRIMARY KEY (multiPrimeID)
);

CREATE TABLE IF NOT EXISTS inProgress (
	instanceID int NOT NULL AUTO_INCREMENT,
  	userID char(30) NOT NULL,
	numStartChecking int NOT NULL,
	numEndChecking int NOT NULL,
    PRIMARY KEY (instanceID)
);

-- ------------------------
-- add starting values-----
-- ------------------------

INSERT INTO multiPrimes (multiPrimeNum)
	VALUES (1);
	
INSERT INTO multiPrimes (multiPrimeNum)
	VALUES (3);

INSERT INTO multiPrimes (multiPrimeNum)
	VALUES (5);