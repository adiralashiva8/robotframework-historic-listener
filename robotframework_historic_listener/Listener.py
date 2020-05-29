import datetime
import mysql.connector
from robot.libraries.BuiltIn import BuiltIn

class Listener:

    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self):
        self.PRE_RUNNER = 0
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_suites = 0
        self.passed_suites = 0
        self.failed_suites = 0
        self.start_time = datetime.datetime.now().time().strftime('%H:%M:%S')
        self.date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def start_suite(self, name, attrs):
        self.test_count = len(attrs['tests'])
        self.suite_name =  name

        # set-up database
        if self.PRE_RUNNER == 0:
            self.HOST = BuiltIn().get_variable_value("${SQL_HOST}",'localhost')
            self.USER_NAME = BuiltIn().get_variable_value("${SQL_USER_NAME}",'superuser')
            self.PASSWORD = BuiltIn().get_variable_value("${SQL_PASSWORD}",'passw0rd')
            self.PROJECT_NAME = BuiltIn().get_variable_value("${RFH_PROJECT_NAME}")
            self.EXECUTION_NAME = BuiltIn().get_variable_value("${RFH_EXECUTION_NAME}")
            self.PRE_RUNNER = 1

            # Connect to db
            self.con = connect_to_mysql_db(self.HOST, self.USER_NAME, self.PASSWORD, self.PROJECT_NAME)
            self.ocon = connect_to_mysql_db(self.HOST, self.USER_NAME, self.PASSWORD, "robothistoric")
            # insert values into execution table
            self.id = insert_into_execution_table(self.con, self.ocon, self.EXECUTION_NAME, 0, 0, 0, 0, 0, 0, 0, self.PROJECT_NAME)

        if self.test_count != 0:
            # suite start time
            self.s_start_time = datetime.datetime.now().time().strftime('%H:%M:%S')
            self.stotal_tests = 0
            self.spassed_tests = 0
            self.sfailed_tests = 0

    def start_test(self, name, attrs):
        if self.test_count != 0:
            self.t_start_time = datetime.datetime.now().time().strftime('%H:%M:%S')

    def end_test(self, name, attrs):
        if self.test_count != 0:
            self.total_tests += 1
            self.stotal_tests += 1

            if attrs['status'] == 'PASS':
                self.passed_tests += 1
                self.spassed_tests += 1
            else:
                self.failed_tests += 1
                self.sfailed_tests += 1

            self.t_end_time = datetime.datetime.now().time().strftime('%H:%M:%S')
            self.t_total_time=(datetime.datetime.strptime(self.t_end_time,'%H:%M:%S') - datetime.datetime.strptime(self.t_start_time,'%H:%M:%S'))
            self.test_exe_time = get_time_in_min(str(self.t_total_time))
            # insert values into test table
            insert_into_test_table(self.con, self.id, self.suite_name + " - " + name, attrs['status'], self.test_exe_time, attrs['message'])

    def end_suite(self, name, attrs):
        self.test_count = len(attrs['tests'])
        if self.test_count != 0:
            self.total_suites += 1

            if attrs['status'] == 'PASS':
                self.passed_suites += 1
            else:
                self.failed_suites += 1

            self.s_end_time = datetime.datetime.now().time().strftime('%H:%M:%S')
            self.s_total_time=(datetime.datetime.strptime(self.s_end_time,'%H:%M:%S') - datetime.datetime.strptime(self.s_start_time,'%H:%M:%S'))
            self.suite_exe_time = get_time_in_min(str(self.s_total_time))
            # insert values into suite table
            insert_into_suite_table(self.con, self.id, name, attrs['status'], self.stotal_tests, self.spassed_tests, self.sfailed_tests, self.suite_exe_time)

    def close(self):
        self.end_time = datetime.datetime.now().time().strftime('%H:%M:%S')
        self.total_time=(datetime.datetime.strptime(self.end_time,'%H:%M:%S') - datetime.datetime.strptime(self.start_time,'%H:%M:%S'))
        self.exe_time = get_time_in_min(str(self.total_time))
        # update execution table values
        update_execution_table(self.con, self.ocon, self.id, self.total_tests, self.passed_tests, self.failed_tests, self.exe_time, self.total_suites, self.passed_suites, self.failed_suites, self.PROJECT_NAME)

'''

# * # * # * # * Re-usable methods out of class * # * # * # * #

'''

def get_time_in_min(time_str):
    h, m, s = time_str.split(':')
    ctime = int(h) * 3600 + int(m) * 60 + int(s)
    crtime = float("{0:.2f}".format(ctime/60))
    return crtime

def connect_to_mysql_db(host, user, pwd, db):
    try:
        mydb = mysql.connector.connect(
            host=host,
            user=user,
            passwd=pwd,
            database=db
        )
        return mydb
    except Exception as e:
        print(e)

def insert_into_execution_table(con, ocon, name, total, passed, failed, ctime, stotal, spass, sfail, projectname):
    cursorObj = con.cursor()
    # rootCursorObj = ocon.cursor()
    sql = "INSERT INTO TB_EXECUTION (Execution_Id, Execution_Date, Execution_Desc, Execution_Total, Execution_Pass, Execution_Fail, Execution_Time, Execution_STotal, Execution_SPass, Execution_SFail) VALUES (%s, now(), %s, %s, %s, %s, %s, %s, %s, %s);"
    val = (0, name, total, passed, failed, ctime, stotal, spass, sfail)
    cursorObj.execute(sql, val)
    con.commit()
    cursorObj.execute("SELECT Execution_Id, Execution_Pass, Execution_Total FROM TB_EXECUTION ORDER BY Execution_Id DESC LIMIT 1;")
    rows = cursorObj.fetchone()
    # update robothistoric.TB_PROJECT table
    # rootCursorObj.execute("UPDATE TB_PROJECT SET Last_Updated = now(), Total_Executions = %s, Recent_Pass_Perc =%s WHERE Project_Name='%s';" % (rows[0], float("{0:.2f}".format((rows[1]/rows[2]*100))), projectname))
    # ocon.commit()
    return str(rows[0])

def update_execution_table(con, ocon, eid, total, passed, failed, duration, stotal, spass, sfail, projectname):
    cursorObj = con.cursor()
    rootCursorObj = ocon.cursor()
    sql = "UPDATE TB_EXECUTION SET Execution_Total=%s, Execution_Pass=%s, Execution_Fail=%s, Execution_Time=%s, Execution_STotal=%s, Execution_SPass=%s, Execution_SFail=%s WHERE Execution_Id=%s;" % (total, passed, failed, duration, stotal, spass, sfail, eid)
    cursorObj.execute(sql)
    con.commit()
    cursorObj.execute("SELECT Execution_Pass, Execution_Total FROM TB_EXECUTION ORDER BY Execution_Id DESC LIMIT 1;")
    rows = cursorObj.fetchone()
    cursorObj.execute("SELECT COUNT(*) FROM TB_EXECUTION;")
    execution_rows = cursorObj.fetchone()
    # update robothistoric.TB_PROJECT table
    rootCursorObj.execute("UPDATE TB_PROJECT SET Last_Updated = now(), Total_Executions = %s, Recent_Pass_Perc =%s WHERE Project_Name='%s';" % (execution_rows[0], float("{0:.2f}".format((rows[0]/rows[1]*100))), projectname))
    ocon.commit()

def insert_into_suite_table(con, eid, name, status, total, passed, failed, duration):
    cursorObj = con.cursor()
    sql = "INSERT INTO TB_SUITE (Suite_Id, Execution_Id, Suite_Name, Suite_Status, Suite_Total, Suite_Pass, Suite_Fail, Suite_Time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    val = (0, eid, name, status, total, passed, failed, duration)
    cursorObj.execute(sql, val)
    # Skip commit to avoid load on db (commit once execution is done as part of close)
    # con.commit()

def insert_into_test_table(con, eid, test, status, duration, msg):
    cursorObj = con.cursor()
    sql = "INSERT INTO TB_TEST (Test_Id, Execution_Id, Test_Name, Test_Status, Test_Time, Test_Error) VALUES (%s, %s, %s, %s, %s, %s)"
    val = (0, eid, test, status, duration, msg)
    cursorObj.execute(sql, val)
    # Skip commit to avoid load on db (commit once execution is done as part of close)
    # con.commit()
