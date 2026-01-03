import mysql.connector
import socket			            #used to find IP address and hostname for userID in multi user mode
import time			                #used for testing, slows program down by 1 second per number
from datetime import datetime       #used to find current time for tracking how long a user has been calculating
import threading                    #used to create multiple threads for event based programming.
import keyboard                     #detects if a key is pressed
import os
import sys
import queue
import time
from collections import deque


display_queue = queue.Queue()
stop_event = threading.Event()

# --------------------------------
# functions for loading settings
# --------------------------------

SETTINGS_FILE = "primeSettings.txt"
REQUIRED_KEYS = {"host", "user", "password", "database", "instance_name"}

#function for loading settings from primeSettings.txt
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return None

    settings = {}
    try:
        with open(SETTINGS_FILE, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    settings[key] = value
    except Exception:
        return None

    if not REQUIRED_KEYS.issubset(settings.keys()):
        return None

    return settings

#function to save settings to primeSettings.txt
def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        for key, value in settings.items():
            f.write(f"{key}={value}\n")

#function to change settings
def prompt_database_settings():
    print("Enter location of the database to be used:")
    print("1 - Localhost from BadPenny")
    print("2 - Odin @ 192.168.1.39 (On HufflepuffCommonroom wifi)")
    print("3 - Odin @ ? (On Speed-Racer wifi)")
    print("4 - Bad Penny 192.168.1.74 (On HufflepuffCommonroom wifi)")
    print("5 - Other location")

    choice = input("> ")

    if choice == "1":
        return {"host": "127.0.0.1", "user": "root", "password": "letmeinnow", "database": "primes"}
    elif choice == "2":
        return {"host": "192.168.1.39", "user": "suirl", "password": "letmeinnow", "database": "primes"}
    elif choice == "3":
        return {"host": "?", "user": "suirl", "password": "letmeinnow", "database": "primes"}
    elif choice == "4":
        return {"host": "192.168.1.74", "user": "root", "password": "letmeinnow", "database": "primes"}
    elif choice == "5":
        host = input("Database IP address: ")
        user = input("Database username: ")
        password = input("Database password: ")
        return {"host": host, "user": user, "password": password, "database": "primes"}
    else:
        print("Invalid choice.")
        return prompt_database_settings()

settings = load_settings()

if settings:
    print("Existing settings found:")
    print(f"Database: {settings['host']} ({settings['database']})")
    print(f"Instance name: {settings['instance_name']}")
    print()
    print("1 - Run with these settings")
    print("2 - Change settings")

    choice = input("> ")

    if choice == "2":
        db_settings = prompt_database_settings()
        instance_name = input("What name would you like this instance to use? ")

        settings = {
            **db_settings,
            "instance_name": instance_name
        }
        save_settings(settings)

else:
    print("No valid settings found. Initial setup required.")
    db_settings = prompt_database_settings()
    instance_name = input("What name would you like this instance to use? ")

    settings = {
        **db_settings,
        "instance_name": instance_name
    }
    save_settings(settings)

databaseHost = [
    settings["host"],
    settings["user"],
    settings["password"],
    settings["database"],
]


# -----------------------------
# functions for multi threading
# -----------------------------


#calculate some primes
def calculating(databaseHost):
    print("Start Calculating\n")

    field = None

    while True:
        #get the next range
        newTestRange = multiLoadRange(databaseHost)
        newTest = newTestRange
        
        #actual calculating
        while newTest <= (newTestRange + 100):
            newTest = newTest + 1
            
            if newTest < 2:
                continue

            is_prime = True
            for x in range(2, int(newTest ** 0.5) + 1):
                if newTest % x == 0:
                    is_prime = False
                    break

            if is_prime:
                print("new prime found")
                multiSavePrime(newTest, databaseHost)
                display_queue.put((newTest, time.perf_counter()))

                #check if its a mesenne prime
                p = newTest

                if p > 0 and ((p + 1) & p) == 0:
                    multiSaveMersenne(newTest, databaseHost)
                    pass           
            
        #ends this task if the userInput task is not still running
        if inputTask.is_alive() == False:
            break

#function for updating the screen and playing the runner
def visualizationLoop(width=100, height=8, fps=30, buffer_size=200):
    field = None

    prime_buffer = deque(maxlen=buffer_size)
    prime_times = deque(maxlen=20)      # for rolling average
    intervals = deque(maxlen=20)

    last_rendered_prime = None
    scroll_accumulator = 0.0

    FRAME_TIME = 1.0 / fps

    while True:

        frame_start = time.perf_counter()

        # Drain incoming messages
        try:
            while True:
                prime, timestamp = display_queue.get_nowait()
                prime_buffer.append(prime)

                if prime_times:
                    intervals.append(timestamp - prime_times[-1])
                prime_times.append(timestamp)
        except queue.Empty:
            pass

        # Determine scroll speed
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            columns_per_second = max(1.0, min(10.0, 1.0 / avg_interval))
        else:
            columns_per_second = 1.0

        scroll_accumulator += columns_per_second * FRAME_TIME

        # Advance field
        while scroll_accumulator >= 1.0:
            scroll_accumulator -= 1.0

            if prime_buffer:
                prime = prime_buffer.popleft()
                last_rendered_prime = prime
                field = generateField(field, prime, width, height)
            else:
                # No new prime — coast terrain
                field = generateField(field, 0, width, height)

        # Render
        if field is not None:
            renderField(
                field,
                width,
                last_rendered_prime if last_rendered_prime else 0,
            )

        # Frame timing
        elapsed = time.perf_counter() - frame_start
        sleep_time = FRAME_TIME - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

        #ends this task if the userInput task is not still running
        if inputTask.is_alive() == False:
            break

#look for the q key to be pressed, and end the task
def userInput():
    print("Start looking for input\n")
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
    userNameInput = settings["instance_name"]
    userName.append(userNameInput)

    #This code will grab the computers host name and ip address to use
    #print("Looking for computers host name\n")
    #hname=socket.gethostname()
    #userName = []
    #userName.append(socket.gethostname())
    #userName.append(socket.gethostbyname(hname))
    
    return userName
    
#function to select items from database. takes in the SQL query as a variable. outputs the result
def multiSelect(sqlInput, databaseHost):

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
def multiUpdate(sqlInput, databaseHost):

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
def multiLoadRange(databaseHost):
    #if there is a range in inProgress table, grab that and add 1 and 100
    sqlInput = "SELECT MAX(numEndChecking) as numStart FROM inProgress;"
    lastRange = multiSelect(sqlInput, databaseHost)
    for x in lastRange:		#lastRange is a list of tuples. iterates through to grab an int.
        for y in x:
            lastRangeInt = y

    #if no range in inProgress, grab last prime found and add 1 and 100
    if lastRangeInt == None:
        sqlInput = "SELECT MAX(multiPrimeNum) as lastPrime FROM multiPrimes;"
        lastRange = multiSelect(sqlInput, databaseHost)
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
    multiUpdate(sqlInput, databaseHost)

    #there can be cases where multiple program instances grab the same range to be checked at the same time. We need to ensure this does not happen.
    #double check that no other instance has the same range as the one just grabbed.
    testCase = 1
    while testCase == 1:
        #grab the last two ranges being checked
        sqlInput = "SELECT MAX(numStartChecking) as secondMax FROM inProgress WHERE numStartChecking NOT IN (SELECT Max(numStartChecking) FROM inProgress);"
        secondMaxRange = multiSelect(sqlInput, databaseHost)
        for x in secondMaxRange:		#isRangeUnique is a list of tuples. iterates through to grab an int.
            for y in x:
                secondMaxInt = y
        sqlInput = "SELECT Max(numStartChecking) as max FROM inProgress;"
        maxRange = multiSelect(sqlInput, databaseHost)
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
            lastRange = multiSelect(sqlInput, databaseHost)
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
            multiUpdate(sqlInput, databaseHost)

        #if there is only one unique case then break the loop and do nothing
        elif isRangeUniqueInt == 0:
            testCase = 0            

    return currentRangeStart

#function to save found prime to the database
# - multiPrimes: multiPrimeID (PRI, int, auto increment), primeIndex(int), multiPrimeNum (int)
# - usersLogged: userID (varchar), IPAddr (varchar), loggedIn (varchar), timeIn (time), timeLogged (time), primesFound (int)
def multiSavePrime(newTest, databaseHost):
    userName = hostName()
    #generate sql to insert new prime
    sqlInput = "INSERT INTO multiPrimes (userID, multiPrimeNum) VALUES ('"+ userName[0] + "', " + str(newTest) + ");"
    multiUpdate(sqlInput, databaseHost)

#function to save found mersenne prime into the database
# - multiPrimes: multiPrimeID (PRI, int, auto increment), primeIndex(int), multiPrimeNum (int)
# - mersennePrimes: mersennePrimeID (PRI, int, auto increment), userID (varchar), primeIndex (int), mersennePrimeNum (int)
# - usersLogged: userID (varchar), IPAddr (varchar), loggedIn (varchar), timeIn (time), timeLogged (time), primesFound (int)
def multiSaveMersenne(newTest, databaseHost):
    userName = hostName()
    #generate sql to insert new prime
    sqlInput = "INSERT INTO mersennePrimes (userID, mersennePrimeNum) VALUES ('"+ userName[0] + "', " + str(newTest) + ");"
    multiUpdate(sqlInput, databaseHost)


# -------------------------------------------------------------------------------------
# Functions for generating side scroller game
# -------------------------------------------------------------------------------------


#function to generate a moving field based on the last prime entered
def generateField(field, prime, width, height):
    """
    field  : list[int] | None
    prime  : int
    width  : int
    height : int
    """

    # Initialize empty field if this is the first run
    if field is None:
        field = [0] * height

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

#function to render the field onto the screen
def renderField(field, width, prime):
    import os

    os.system("cls" if os.name == "nt" else "clear")

    height = len(field)

    BLUE  = "\033[94m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    # Pre-calc column densities
    column_ones = [0] * width
    for row in field:
        for x in range(width):
            if (row >> (width - 1 - x)) & 1:
                column_ones[x] += 1

    # Render top → bottom
    for y in range(height):
        line = ""
        for x in range(width):
            bit = (field[y] >> (width - 1 - x)) & 1
            if bit:
                color = BLUE if column_ones[x] <= 3 else GREEN
                line += f"{color}█{RESET}"
            else:
                line += " "
        print(line)

    print("-" * width)
    print(f"Last prime: {prime}")


# ------------------
# main program start
# ------------------

#create task variables attached to functions
calculatingTask = threading.Thread(target=calculating, args=(databaseHost,), name='calculatingTask')
inputTask = threading.Thread(target=userInput, name='inputTask')
#visualizationTask = threading.Thread(target=visualizationLoop, name='screeTask')

#start a task for calculating, updating the screen, and a task to look for user input 'q' to quit the program
print("Calculating task starting.\n")
calculatingTask.start()
print("Looking for user input task starting.\n")
inputTask.start()
print("starting the screen task")
#visualizationTask.start()

#once all concurrent tasks end, we continue.
calculatingTask.join()
inputTask.join()
#visualizationTask.join()

print("all tasks complete.\n")