#!/usr/bin/env python

### jobcal
## Byron Vickers, Jul 2014

# BUGS:
# 'listall' does not list in date order. Iterate over items.sorted or whatever. Or use an auto-ordered datastruct?

# TODO:
# Allow dmy_parse to accept 'y.*' as 'yesterday' (today minus 1 day)
# Simulataneous display of multiple calendars
# Moving of events
# Print calendar on load request (not load to function, but "load" the entered command)
# Assign entries before 5 or 6 am as yesterday (??)
#
# Clean up loading of jobcal properties (dictionary with update?)
# Break input handlers into functions, use dictionary to map input to function. 
# Add exception handling decorators to (TBI) handler functions so as to avoid exit
# Colour prefs (?)
# Change input order to allow description last (and date parse stops on encountering non-date string -- via exception?)

import datetime
import calendar
import itertools
import sys
import readline
import pickle
import shlex
import os

# Not certain, but I suspect these probably don't work on Windows. Not sure about Linux.
class termcols:
    endc = '\033[0m'
    main = '\033[99m'
    cols = {
        'red' : '\033[91m',
        'green' : '\033[92m',
        'blue' : '\033[94m',
        'cyan' : '\033[96m',
        'white' : '\033[97m',
        'yellow' : '\033[93m',
        'magenta' : '\033[95m',
        'grey' : '\033[90m',
        'black' : '\033[90m',
    }

class WorkSession(object):
    "One 'session' of work. Sits within the owning JobCal's list for the relevant day"
    def __init__(self, parent, hours, desc):
        self.parent = parent
        self.hours = hours
        self.desc = desc
        
    def edit(self, hours, desc):
        if hours > 0:
            self.hours = hours
            self.desc = desc
        else:
            yn = raw_input("Hours are not positive! Are you sure you want to proceed? y/N: ")
            if yn[0].lower() == 'y':
                self.hours = hours
                self.desc = desc
            else:
                pass
        
class WorkDay(object):
    "A day on which work was (probably) done! Just a holder for the list of WorkSessions"
    def __init__(self, parent, date):
        self.parent = parent
        self.date = date
        self.sessions = list()
        
    def add_session(self, hours, desc):
        self.sessions.append(WorkSession(self, hours, desc))
        print("Session added to {0} ({1:.2f}h, '{2}').".format(self.date.strftime('%d %b %Y'), hours, desc))
        
    def del_session(self, entry):
        try:
            session = self.sessions[entry]
            if entry < len(self.sessions)-1:
                warning = " [Indices updated]"
            else:
                warning = ""
            hours = session.hours
            desc = session.desc
            del(self.sessions[entry])
            print("Session [{0}] deleted from {1} ({2:.2f}h, '{3}').{4}".format(entry, self.date.strftime('%d %b %Y'), hours, desc, warning))
        except KeyError:
            print("Index {0} is too large for list of sessions on day {1}".format(entry, self.date.strftime('%d %b %Y')))
            
    def edit_session(self, entry, hours, desc):
        try:
            self.sessions[entry].edit(hours, desc)
        except KeyError:
            print("Index {0} is too large for list of sessions on day {1}".format(entry, self.date.strftime('%d %b %Y')))
        
    def get_total(self):
        return sum([session.hours for session in self.sessions])
        

class JobCal(object):
    "Calendar object with additional work information"
    def __init__(self, filename=''):
        if filename=='':
            filename = "default.jobcal"
        self.load(filename)
        
    def save_dec(func):
        # function decorator to save jobcal after function execution
        def inner(self, *args, **kwargs):
            func(self, *args,**kwargs)
            self.save(self.filename)
        return inner
        
    def save(self, filename=''):
        if filename == '':
            filename = self.filename
        file = open(filename, 'w')
        pickle.dump(self, file)
        file.close()
    
    @save_dec  
    def load(self, filename=''):
        if filename == '':
            filename = self.filename
        try:
            file = open(filename, 'r')
            jctemp = pickle.load(file)
            self.dict = jctemp.dict
            self.cal = jctemp.cal
            self.textcal = jctemp.textcal
            self.starttime = jctemp.starttime
            self.startdesc = jctemp.startdesc
            self.filename = filename
            self.name = self.filename.split('.')[0]   
            file.close()
            print("Opened {0}".format(filename))
            if self.starttime:
                print("Stopwatch is running ({0:.2f}h, '{1}')".format((datetime.datetime.now()-self.starttime).total_seconds()/(60*60), self.startdesc))
        except IOError:
            print("Cannot load from file {0}. Creating empty calendar.".format(filename))
            # default (empty) values
            self.dict = dict()
            self.cal = calendar.Calendar()
            self.textcal = calendar.TextCalendar()
            self.starttime = None
            self.startdesc = None
            self.filename = filename
            self.name = self.filename.split('.')[0] 
        
    @save_dec
    def add_session(self,date,hours,desc=''):
        try:
            self.dict[date].add_session(hours,desc)
        except KeyError:
            self.dict[date] = WorkDay(self, date)
            self.dict[date].add_session(hours, desc)
    
    @save_dec
    def del_session(self,date,entry):
        try:
            self.dict[date].del_session(entry)
            if len(self.dict[date].sessions) == 0:
                del(self.dict[date])
        except KeyError:
            print("No sessions recorded for {0}".format(date.strftime('%d %b %Y')))
    
    @save_dec
    def edit_session(self, date, entry, hours, desc=''):
        try:
            self.dict[date].edit_session(entry, hours, desc)
        except KeyError:
            print("No sessions recorded for {0}".format(date.strftime('%d %b %Y')))
            
    def print_month(self, year, month, col='grey'):
        print(''.join([termcols.cols[col], '{:^20}'.format(self.name.title()), termcols.endc]))
        str1 = self.textcal.formatmonth(year,month).splitlines()
        str2 = []
        formstr = '{:>2}'
        for week in self.cal.monthdatescalendar(year, month):
            str_temp = []
            tot = 0
            for date in week:
                try:
                    val = self.dict[date].get_total()
                    str_temp.append(formstr.format(str(int(val))))
                    tot += val
                except KeyError:
                    str_temp.append(formstr.format('0'))
            str_temp.append('| {0:.1f}'.format(tot))
            str2.append(str_temp)
        print(str1[0])
        print(str1[1])
        monthdays = str1[2:]
        for i in range(len(monthdays)):
            print(''.join([termcols.main, monthdays[i], termcols.endc]))
            print(''.join([termcols.cols[col], ' '.join(str2[i]), termcols.endc]))
            
    def list_day(self, year, month, day):
        date = datetime.date(year, month, day)
        try:
            workday = self.dict[date]
            print("{0}: {1:.2f}h".format(date.strftime('%d %b %Y'), workday.get_total()))
            i=0
            for session in workday.sessions:
                print("--[{0}] {1:.2f}h '{2}'".format(i, session.hours, session.desc))
                i += 1
        except KeyError:
            print("{0}: 0h".format(date.strftime('%d %b %Y')))
            print("--No sessions recorded for {0}".format(date.strftime('%d %b %Y')))
            
    def list_month(self, year, month):
        tot = 0
        for date, workday in self.dict.iteritems():
            
            self.list_day(date.year, date.month, date.day)
            tot += workday.get_total()
        print("TOTAL: {0:.2f}h".format(tot))
    
    @save_dec
    def start(self, desc=''):
        self.starttime = datetime.datetime.now()
        self.startdesc = desc
        print("Starting stopwatch")
    
    @save_dec
    def stop(self):
        delta = datetime.datetime.now() - self.starttime
        self.add_session(self.starttime.date(), delta.total_seconds()/(60*60), self.startdesc)
        self.clear()
    
    @save_dec    
    def clear(self):
        self.starttime = None
        self.startdesc = None
        print("Stopwatch cleared")

class Prefs(object):
    def __init__(self):
        self.dict = {
            # default values
            'filename' : 'default.jobcal',
            'prompt' : 'What would you like to do?',
            'colour' : 'grey',
        }
        self.load()
        
    def __getitem__(self, item):
        return self.dict.__getitem__(item)
        
    def update(self, newdict):
        self.dict.update(newdict)
        self.save()
        
    def change_colour(self, colour):
        if colour in termcols.cols:
            self.dict['colour'] = colour
            print("Colour changed to {0}".format(colour))
            self.save()
        else:
            print("Colour not available. Colours are:")
            for col in termcols.cols:
                print("--{0}".format(col))
    
    def save(self):
        try:
            prefs_file = open('jcprefs','w')
            pickle.dump(self,prefs_file)
            prefs_file.close()
        except IOError:
            print("Could not save preference file jcprefs.")
            
    def load(self):
        try:
            prefs_file = open(os.path.expanduser('jcprefs'),'r')
            self.dict.update(pickle.load(prefs_file).dict)
            prefs_file.close()
        except IOError, AttributeError:
            print("Could not load from preference file jcprefs. Using default settings.")

def my_parse(input):
    dateparse = datetime.datetime.strptime
    today = datetime.date.today()
    month = today.month
    year = today.year
    if len(input) >= 1:
        try:
            month = dateparse(input[0],'%m').month
        except:
            month = dateparse(input[0],'%b').month
    if len(input) >= 2:
        try:
            year = dateparse(input[1],'%y').year
        except:
            year = dateparse(input[1],'%Y').year
    return (year, month)

def dmy_parse(input):
    dateparse = datetime.datetime.strptime
    today = datetime.date.today()
    day = today.day
    month = today.month
    year = today.year
    if len(input) >= 1:
        day = dateparse(input[0], '%d').day
    year, month = my_parse(input[1:])
    return (year, month, day)
            
if __name__ == '__main__':
    today = datetime.date.today()
    dateparse = datetime.datetime.strptime
    workdir = os.path.expanduser('~/Documents/jobcal')
    try:
        os.chdir(workdir)
    except OSError:
        os.mkdir(workdir)
        os.chdir(workdir)
    prefs = Prefs()
    jobcal = JobCal(prefs['filename'])
    loop = True
    firsttime = True
    while(loop):
        if len(sys.argv) == 1:
            if firsttime:
                jobcal.print_month(today.year, today.month, col=prefs['colour'])
            input = shlex.split(raw_input("{0} ".format(prefs['prompt'])))
        else:
            input = sys.argv[1:]
            loop = False
        if len(input) == 0:
            continue
        if input[0] in ['help','?','h']:
            print(
                """--------------------------------------------------------
Valid commands are:
    --- display functions ---
    print [<month> [<year>]
    list [<day> [<month> [<year>]]]
    listall [<month> [<year>]]
    --- calendar edit functions ---
    add <num_hours> [<desc> [<day> [<month> [<year>]]]]
    del <entry_no> [<day> [<month> [<year>]]]
    edit <entry_no> [<day> [<month> [<year>]]]
    --- job stopwatch functions ---
    start [<desc>]
    stop
    clear
    --- utility functions ---
    load <calendar>
    chprompt [<new_prompt>]
    chcol [<new_col>]
    help
    quit
    
Missing day/month/year values default to those of current day.

Email the author at byron.vickers@gmail.com
--------------------------------------------------------""")
        elif input[0] in ["print","p"]:
            ym_pars = my_parse(input[1:])
            jobcal.print_month(*ym_pars, col=prefs['colour'])
        elif input[0] in ["list", "li"]:
            ymd_pars = dmy_parse(input[1:])
            jobcal.list_day(*ymd_pars)
        elif input[0] in ["listall", "la"]:
            ym_pars = my_parse(input[1:])
            jobcal.list_month(*ym_pars)
        elif input[0] in ["add", "a"]:
            num_hours = input[1]
            desc = ''
            if len(input) >= 3:
                desc = input[2]
            ymd_pars = dmy_parse(input[3:])
            jobcal.add_session(datetime.date(*ymd_pars), float(num_hours), desc)
        elif input[0] in ["del","d"]:
            entry_no = input[1]
            ymd_pars = dmy_parse(input[2:])
            jobcal.del_session(datetime.date(*ymd_pars), int(entry_no))
        elif input[0] in ["edit", "e"]:
            entry_no = input[1]
            num_hours = input[2]
            desc = input[3]
            ymd_pars = dmy_parse(input[4:])
            jobcal.edit_session(datetime.date(*ymd_pars), int(entry_no), float(num_hours), desc)
        elif input[0] in ["start", "in", "clockin", "ci"]:
            desc = ''
            if len(input) >= 2:
                desc = input[1]
            jobcal.start(desc)
        elif input[0] in ["stop", "out", "clockout", "co"]:
            jobcal.stop()
        elif input[0] in ["clear", "c"]:
            jobcal.clear()
        elif input[0] in ["chprompt", "chp"]:
            try:
                prefs.update({'prompt' : input[1]})
            except IndexError:
                prefs.update({'prompt' : "What would you like to do?"})
        elif input[0] in ["chcolour", "chcol", "chc"]:
            try:
                prefs.change_colour(input[1])
            except IndexError:
                prefs.change_colour("grey")
        elif input[0] in ["load", "l"]:
            filename = input[1]
            if not "." in filename:
                filename += ".jobcal"
            prefs.update({'filename' : filename})
            jobcal.load(filename)
        elif input[0] in ["quit","q"]:
            loop = False
        else:
            print("Command unrecognised. Use 'help' for command list")
        firsttime = False
            
        
        



