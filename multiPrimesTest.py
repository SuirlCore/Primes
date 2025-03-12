import mysql.connector
import socket			    #used to find IP address and hostname for userID in multi user mode
import time			    #used for testing, slows program down by 1 second per number
from datetime import datetime       #used to find current time for tracking how long a user has been calculating
import psutil

#set the database variables
databaseHost = ["192.168.1.73", "suirl", "letmeinnow", "primes"]

#grab info from the user
print("whats the IP for the database:")
databaseHost[0] = input(">")
print("What time delay would you like to use? (0.05 works for RPI 3b+)")
timeDelay = input(">")

#grab the computers hostname
userNameInput = socket.gethostname()

# -----------------------------
# functions for multi threading
# -----------------------------


#calculate some primes
def calculating():
    print("Start Calculating\n")

    while True:
        #get the next range
        newTestRange = multiLoadRange()
        newTest = newTestRange
        print("starting a new range: " + str(newTestRange) + " - " + str((newTestRange + 100)))
        
        #actual calculating
        while newTest <= (newTestRange + 100):
            newTest = newTest + 1
            x = 0
            divisors = 0
            while (x < (newTest / 2)) and (divisors <= 1):
                x = x + 1
                if newTest % x == 0:
                    divisors = divisors + 1
            if divisors <= 1:
                print("New prime found: " + str(newTest))
                multiSavePrime(newTest)

            #slow things down a bit.
            time.sleep(float(timeDelay))

        #edit the database to show the range has been completed
        sqlInput = "UPDATE inProgress SET inProgress = '0' WHERE userID = '" + userNameInput + "';"
        multiUpdate(sqlInput)


# -------------------------------------------------------------------------------------
# Functions for multi user loading, holding spot, and saving primes to MariaDB database
# -------------------------------------------------------------------------------------


#function to find current users IP and localhost name. returns userName[] index 0 = name, index 1 = IP
def hostName():
    #This code grabs the computers information that the user provided at the beginning of the program
    userName = []
    userName.append(userNameInput)

    #This code will grab the computers host name and ip address to use
    #print("Looking for computers host name\n")
    #hname=socket.gethostname()
    #userName = []
    #userName.append(socket.gethostname())
    #userName.append(socket.gethostbyname(hname))
    
    return userName
    
#function to select items from database. takes in the SQL query as a variable. outputs the result
def multiSelect(sqlInput):

    #connect to the database
    mydb = mysql.connector.connect (
	host = databaseHost[0],
	user = databaseHost[1],
	password = databaseHost[2],
	database = databaseHost[3]
    )
    mycursor = mydb.cursor()

    #SQL statement to run the SQL statement
    mycursor.execute(sqlInput)
    myresult = mycursor.fetchall()
    return myresult

#function to update the database. Takes in the SQL update query as a variable.
def multiUpdate(sqlInput):

    #connect to the database
    mydb = mysql.connector.connect (
    	host = databaseHost[0],
    	user = databaseHost[1],
    	password = databaseHost[2],
    	database = databaseHost[3]
    )
    mycursor = mydb.cursor()

    #insert the SQL statement into the database
    mycursor.execute(sqlInput)
    mydb.commit()

#function to load the last range that was checked
# - multiPrimes: multiPrimeID (PRI, int, auto increment), primeIndex(int), multiPrimeNum (int)
# - inProgress: instanceID (PRI, int, auto increment), userID (varchar), numStartChecking (int), numEndChecking (int)
def multiLoadRange():
    print("Pulling the next range from the database\n")
    userName = userNameInput
    
    # Check if there is an existing inProgress range for the current hostname
    sqlInput = f"""
        SELECT numStartChecking, numEndChecking FROM inProgress 
        WHERE userID = '{userName}' AND inProgress = 1 
        LIMIT 1;
    """
    existingRange = multiSelect(sqlInput)
    
    if existingRange:
        currentRangeStart, currentRangeEnd = existingRange[0]
        print(f"Using existing range: {currentRangeStart} - {currentRangeEnd}")
        
        # Delete existing primes in the selected range
        sqlInput = f"""
            DELETE FROM multiPrimes WHERE multiPrimeNum BETWEEN {currentRangeStart} AND {currentRangeEnd};
        """
        multiUpdate(sqlInput)
    else:
        # If no existing range, find the last checked range
        sqlInput = "SELECT MAX(numEndChecking) as numStart FROM inProgress;"
        lastRange = multiSelect(sqlInput)
        lastRangeInt = next((y for x in lastRange for y in x), None)
        
        # If no range found, use the last prime found
        if lastRangeInt is None:
            sqlInput = "SELECT MAX(multiPrimeNum) as lastPrime FROM multiPrimes;"
            lastRange = multiSelect(sqlInput)
            lastRangeInt = next((y for x in lastRange for y in x), None)

        if lastRangeInt is None:
            lastRangeInt = 0
        currentRangeStart = lastRangeInt + 1
        currentRangeEnd = currentRangeStart + 100

        # Insert new range into inProgress table
        sqlInput = f"""
            INSERT INTO inProgress (userID, numStartChecking, numEndChecking, inProgress)
            VALUES ('{userName}', {currentRangeStart}, {currentRangeEnd}, 1);
        """
        multiUpdate(sqlInput)
    
    # Existing logic for handling multiple instances
    testCase = 1
    while testCase == 1:
        sqlInput = "SELECT MAX(numStartChecking) as secondMax FROM inProgress WHERE numStartChecking NOT IN (SELECT Max(numStartChecking) FROM inProgress);"
        secondMaxRange = multiSelect(sqlInput)
        for x in secondMaxRange:
            for y in x:
                secondMaxInt = y
        sqlInput = "SELECT Max(numStartChecking) as max FROM inProgress;"
        maxRange = multiSelect(sqlInput)
        for x in maxRange:
            for y in x:
                maxInt = y

        if secondMaxInt == 1:
            isRangeUniqueInt = 0
        elif secondMaxInt != 1:
            if maxInt <= (secondMaxInt + 100):
                isRangeUniqueInt = 1
            elif maxInt > (secondMaxInt + 100):
                isRangeUniqueInt = 0

        if isRangeUniqueInt == 1: 
            print("adding the next range.")
            sqlInput = "SELECT MAX(multiPrimeNum) as lastPrime FROM multiPrimes;"
            lastRange = multiSelect(sqlInput)
            for x in lastRange:
                for y in x:
                    lastRangeInt = y

            if lastRangeInt is None:
                lastRangeInt = 0
            currentRangeStart = lastRangeInt + 1
            currentRangeEnd = currentRangeStart + 100
            userName = hostName()
            sqlInput = "INSERT INTO inProgress (userID, numStartChecking, numEndChecking) VALUES ('" + str(userName[0]) + "', " + str(currentRangeStart) + ", " + str(currentRangeEnd) + ");"
            multiUpdate(sqlInput)

        elif isRangeUniqueInt == 0:
            testCase = 0            

    return currentRangeStart


#function to save found prime to the database
# - multiPrimes: multiPrimeID (PRI, int, auto increment), primeIndex(int), multiPrimeNum (int)
# - usersLogged: userID (varchar), IPAddr (varchar), loggedIn (varchar), timeIn (time), timeLogged (time), primesFound (int)
def multiSavePrime(newTest):
    userName = hostName()
    #generate sql to insert new prime
    sqlInput = "INSERT INTO multiPrimes (userID, multiPrimeNum) VALUES ('"+ userName[0] + "', " + str(newTest) + ");"
    multiUpdate(sqlInput)
    

# ------------------
# main program start
# ------------------

calculating()
