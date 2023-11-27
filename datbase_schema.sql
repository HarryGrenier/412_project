CREATE TABLE Users (
  UserID SERIAL PRIMARY KEY,
  FirstName VARCHAR(255) NOT NULL,
  LastName VARCHAR(255) NOT NULL,
  Email VARCHAR(255) NOT NULL UNIQUE,
  Password VARCHAR(255) NOT NULL,
  DateJoined DATE NOT NULL
);


CREATE TABLE Groups (
  GroupID SERIAL PRIMARY KEY,
  GroupName VARCHAR(255) NOT NULL,
  Description TEXT,
  GroupGoal DECIMAL(10, 2) DEFAULT 0,
  CurrentGroupSavings DECIMAL(10, 2) DEFAULT 0
);

CREATE TABLE Expenses (
  ExpenseID SERIAL PRIMARY KEY,
  UserID INT,
  Amount DECIMAL(10, 2) NOT NULL,
  Category VARCHAR(255) NOT NULL,
  Date DATE NOT NULL,
  FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE SET NULL
);

CREATE TABLE Savings (
  SavingsID SERIAL PRIMARY KEY,
  UserID INT,
  Amount DECIMAL(10, 2) NOT NULL,
  Purpose VARCHAR(255) NOT NULL,
  Date DATE NOT NULL,
  FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE SET NULL
);

CREATE TABLE Challenges (
  ChallengeID SERIAL PRIMARY KEY,
  Name VARCHAR(255) NOT NULL,
  BriefDescription VARCHAR(255),
  Description TEXT,
  StartDate DATE NOT NULL,
  EndDate DATE NOT NULL,
  TargetAmount DECIMAL(10, 2) DEFAULT 0
);

CREATE TABLE UserGroups (
  UserID INT,
  GroupID INT,
  PRIMARY KEY (UserID, GroupID),
  FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
  FOREIGN KEY (GroupID) REFERENCES Groups(GroupID) ON DELETE CASCADE
);

CREATE TABLE UserChallenges (
  UserID INT,
  ChallengeID INT,
  PRIMARY KEY (UserID, ChallengeID),
  FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
  FOREIGN KEY (ChallengeID) REFERENCES Challenges(ChallengeID) ON DELETE CASCADE
);