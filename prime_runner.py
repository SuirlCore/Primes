import mysql.connector
import socket			    #used to find IP address and hostname for userID in multi user mode
import time			    #used for testing, slows program down by 1 second per number
from datetime import datetime       #used to find current time for tracking how long a user has been calculating
import threading                    #used to create multiple threads for event based programming.
import keyboard                     #detects if a key is pressed

#database connection information. hostname, username, password, database name.
#gather login information for the database
print("Enter location of the database to be used:")
print("1 - Localhost from BadPenny")
print("2 - Odin @ 192.168.1.39 (On HufflepuffCommonroom wifi)")
print("3 - Odin @ ? (On Speed-Racer wifi)")
print("4 - Bad Penny 192.168.1.74 (On HufflepuffCommonroom wifi)")
print("5 - Other location")
databaseLocation = input()
if databaseLocation == "1":
    databaseHost = ["127.0.0.1", "root", "letmeinnow", "primes"]
elif databaseLocation == "2":
    databaseHost = ["192.168.1.39", "suirl", "letmeinnow", "primes"]
elif databaseLocation == "3":
    databaseHost = ["?", "suirl", "letmeinnow", "primes"]
elif databaseLocation == "4":
    databaseHost = ["192.168.1.74", "root", "letmeinnow", "primes"]
elif databaseLocation == "5":
    print("Please enter the IP address for the database")
    databaseIPAddress = input()
    print("What is the username for the database?")
    databaseUsername = input()
    print("What is the password for the database?")
    databasePassword = input()
    databaseHost = [databaseIPAddress, databaseUsername, databasePassword, "primes"]

#grab the computers username from the user
print("What name would you like this instance to use?")
userNameInput = input()

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
                multiSavePrime(newTest)
            
        #ends this task if the userInput task is not still running
        if inputTask.is_alive() == False:
            break

#look for the q key to be pressed, and end the task
def userInput():
    while True:
        if keyboard.is_pressed('q'):
            break


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
    #if there is a range in inProgress table, grab that and add 1 and 100
    sqlInput = "SELECT MAX(numEndChecking) as numStart FROM inProgress;"
    lastRange = multiSelect(sqlInput)
    for x in lastRange:		#lastRange is a list of tuples. iterates through to grab an int.
        for y in x:
            lastRangeInt = y

    #if no range in inProgress, grab last prime found and add 1 and 100
    if lastRangeInt == None:
        sqlInput = "SELECT MAX(multiPrimeNum) as lastPrime FROM multiPrimes;"
        lastRange = multiSelect(sqlInput)
        for x in lastRange:		#lastPrime is a list of tuples. iterates through to grab an int.
            for y in x:
                lastRangeInt = y

    #add new range to be checked to inProgress table
    if lastRangeInt == None:
        lastRangeInt = 0
    currentRangeStart = lastRangeInt + 1
    currentRangeEnd = currentRangeStart + 100
    userName = hostName()
    sqlInput = "INSERT INTO inProgress (userID, numStartChecking, numEndChecking) VALUES ('" + str(userName[0]) + "', " + str(currentRangeStart) + ", " + str(currentRangeEnd) + ");"
    multiUpdate(sqlInput)

    #there can be cases where multiple program instances grab the same range to be checked at the same time. We need to ensure this does not happen.
    #double check that no other instance has the same range as the one just grabbed.
    testCase = 1
    while testCase == 1:
        #grab the last two ranges being checked
        sqlInput = "SELECT MAX(numStartChecking) as secondMax FROM inProgress WHERE numStartChecking NOT IN (SELECT Max(numStartChecking) FROM inProgress);"
        secondMaxRange = multiSelect(sqlInput)
        for x in secondMaxRange:		#isRangeUnique is a list of tuples. iterates through to grab an int.
            for y in x:
                secondMaxInt = y
        sqlInput = "SELECT Max(numStartChecking) as max FROM inProgress;"
        maxRange = multiSelect(sqlInput)
        for x in maxRange:		#isRangeUnique is a list of tuples. iterates through to grab an int.
            for y in x:
                maxInt = y

        if secondMaxInt == 1:
            #when database is first created, there is no second range to test against, so we skip this test entirely.
            isRangeUniqueInt = 0
        elif secondMaxInt != 1:
            #check if the max and secondMax overlap
            if maxInt <= (secondMaxInt + 100):
                isRangeUniqueInt = 1    #ranges overlap, need a new range
            elif maxInt > (secondMaxInt + 100):
                isRangeUniqueInt = 0    #ranges do not overlap. all good.

        #if there are multiple instances of the last range being checked then do this
        if isRangeUniqueInt == 1: 
            sqlInput = "SELECT MAX(multiPrimeNum) as lastPrime FROM multiPrimes;"
            lastRange = multiSelect(sqlInput)
            for x in lastRange:		#lastPrime is a list of tuples. iterates through to grab an int.
                for y in x:
                    lastRangeInt = y

            #add new range to be checked to inProgress table
            if lastRangeInt == None:
                lastRangeInt = 0
            currentRangeStart = lastRangeInt + 1
            currentRangeEnd = currentRangeStart + 100
            userName = hostName()
            sqlInput = "INSERT INTO inProgress (userID, numStartChecking, numEndChecking) VALUES ('" + str(userName[0]) + "', " + str(currentRangeStart) + ", " + str(currentRangeEnd) + ");"
            multiUpdate(sqlInput)

        #if there is only one unique case then break the loop and do nothing
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

    #calculate whether this prime is a mersenne prime, and insert it into the database if it is
    mersenneTest = 2^newTest-1
    x = 0
    divisors = 0
    while (x < (mersenneTest / 2)) and (divisors <= 1):
        x = x + 1
        if newTest % x == 0:
            divisors = divisors + 1
    if divisors <= 1:
        multiSavePrime(newTest)


    multiUpdate(sqlInput)


# -------------------------------------------------------------------------------------
# Functions for generating side scroller game
# -------------------------------------------------------------------------------------


#function to generate a moving field based on the last prime entered
def scroll_field_with_prime_gravity(field, prime, width):
    """
    field  : list[int]   # one int per row
    prime  : int         # arbitrarily large
    width  : int         # horizontal size
    """

    height = len(field)

    # 1. Scroll field left
    mask = (1 << width) - 1
    field = [(row << 1) & mask for row in field]

    # 2. Sample ONLY the lowest `height` bits of the prime
    bits = [(prime >> i) & 1 for i in range(height)]

    # 3. Flip vertically
    bits.reverse()

    # 4. Gravity: pack 1s at bottom
    ones = sum(bits)
    new_column = [0] * (height - ones) + [1] * ones

    # 5. Insert column
    for row_index in range(height):
        field[row_index] |= new_column[row_index]

    return field

#function to input field, and display it on the screen

# ------------------
# main program start
# ------------------

#create task variables attached to functions
calculatingTask = threading.Thread(target=calculating, name='calculatingTask')
inputTask = threading.Thread(target=userInput, name='inputTask')

#start a task for calculating, and a task to look for user input 'q' to quit the program
print("Calculating task starting.\n")
calculatingTask.start()
print("Looking for user input task starting.\n")
inputTask.start()

#once both concurrent tasks end, we continue.
calculatingTask.join()
inputTask.join()

print("all tasks complete.\n")
