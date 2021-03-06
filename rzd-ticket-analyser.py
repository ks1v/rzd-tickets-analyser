#!/usr/bin/python
# -*- coding: UTF-8 -*-

__author__  = 'Andrew ks1v Kiselev'
__email__   = "mail@andrewkiselev.com"
__year__    = "2012"
__title__   = "RZD tickets analyser"
__version__ = '2.2'


from httplib2   import Http                 # Downloading
from urllib     import urlencode            # Downloading
from datetime   import datetime, timedelta  # Parsing, Statistic
from re         import finditer, escape     # Parsing
from string     import find                 # Parsing
from hashlib    import md5                  # Serialization
from pickle     import dump, load           # Serialization
import numpy                                # Statistic
import os                                   # DeSerialization
import sys                                  # Commands parsing
import ConfigParser                         # Configuration file

# == Next ==
# TODO Testing - Accounts

# CONFIG

def getConfig(path) :
    """
    getOptions(path)   
        read options from config file using ConfigParser module
        returns dict of options
    """ 
    try: 
        config = ConfigParser.ConfigParser()
        with open(path, 'r') as fd :
            config.readfp(fd)
    except IOError :
        print "ERROR! Cannot load config from " + path + "!\n"
        sys.exit()
    except ConfigParser.Error :
        print "ERROR! Some ConfigParser error.\n"
        sys.exit()
    else :
        print '\nConfig loaded\n'
            
    
    cfg = {}
    for section in config.sections() :
        for option in config.options(section) :
            cfg[option] = config.get(section, option)
            
    return cfg
        
        
def checkConfig(cfg) :
    """
    checkConfig(cfg)
        check config dict for errors 
    """
    
    if not type(cfg) == type({}) :
        print 'ERROR! Config variable is not a dictionary!'
        sys.exit()
    
    mandatory_list = ['login', 'password', 'delimiter', 'datetime_format', 
                      'default_city', 'default_passenger', 'path_dir', 
                      'path_pages', 'path_tickets', 'path_table', 'host', 
                      'auth_page', 'error_page', 'current_page_mark', 
                      'next_page_url_mark', 'next_page_url_end_mark', 
                      'cabinet_url', 'ticket_url_mark', 'ticket_url_end_mark', 
                      'passenger_end_mark', 'route_middle_mark']
 
    cfg_fields = set(cfg.keys())
    mandatory_set = set(mandatory_list)
    diff = mandatory_set - cfg_fields
    
    if diff :
        # diff isn't empty => not all field are filled'
        print "ERROR! Not all mandatory fields of the config are filled." 
        print "Missing fields: " 
        for it in diff : print '\t- ' + str(it)
        sys.exit()
                        
                        

# SITE

def rzdAuth(cfg) :   
    """
    rzdAuth(cfg)
        cfg — dict with 'login' and 'password' fields
        return [http, headers]
            http - http object
            headers - headers with cookies
    """
    
    auth_page  = cfg['host'] + cfg['auth_page']  
    error_page = cfg['host'] + cfg['error_page']  
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    auth_form = { "j_username" : cfg['login'],
                  "j_password" : cfg['password'],
                  "action.x"   : "53",
                  "action.y"   : "10",
                  "action"     : "Вход"}

    # HTTP object creation
    http = Http(disable_ssl_certificate_validation = True)

    # Authentication
    print "Login as " + cfg['login'] + '.'
    response = http.request(auth_page, "POST", headers = headers, \
                                                body = urlencode(auth_form))
    
    if response[0]['location'] == error_page :
        print "\tAuthentication Failed."
        sys.exit()
    else :
        print "\tAuthentication OK."
        headers['Cookie'] = response[0]['set-cookie']


    return http, headers

def nextCabinetPageURLPosition(cabinet_page, cfg) :
    """
    nextCabinetPageURLPosition(cabinet_page)
        returns numerical position of the next cabinet page or -1 o/w
    """

    mark_pos = find(cabinet_page, cfg['current_page_mark'])
    next_page_pos = find(cabinet_page, cfg['next_page_url_mark'], mark_pos)
    return next_page_pos

def nextCabinetPageURLExtraction(cabinet_page, next_page_url_pos, cfg) :
    """
    nextCabinetPageURLExtraction(cabinet_page, next_page_url_pos)
        returns URL of the next cabinet page
    """

    start_pos = next_page_url_pos
    end_pos = start_pos + find(cabinet_page[start_pos : start_pos + 200], \
                cfg['next_page_url_end_mark'])
    next_page_url = cabinet_page[start_pos : end_pos]

    # httplib2 understands only absolute URLs
    if not next_page_url.startswith(cfg['host']) :
        next_page_url = cfg['host'] + next_page_url


    return next_page_url

def getTicketURLs(http, headers, cfg) :
    """
    getTicketURLs(http, headers)
        returns list of URLs of tickets from the account ('http', 'headers')
    """

    ticket_urls = []
    
    while True :

        print "\nCabinet page is found at ", cfg['cabinet_url']

        # Fetch new cabinet page
        response, cabinet_page = http.request(cfg['cabinet_url'], "GET", \
                                                        headers = headers)
        print "\tRequest... " + response['status'] + '.'

        # Tickets existence check
        urls_tickets_positions = findAll(cabinet_page, cfg['ticket_url_mark'])

        if len(urls_tickets_positions) == 0 :
            print "\tThere are no tickets here :("
            break
        else :
            print "\tFound " + str(len(urls_tickets_positions))+" tickets."

            # Extraction tickets' URLs
            ticket_urls.extend(ticketURLsExtraction(cabinet_page, 
                                                urls_tickets_positions, cfg))

            # Next cabinet page url searching

            next_page_url_pos = nextCabinetPageURLPosition(cabinet_page, cfg)

            if next_page_url_pos == -1 :
                # No more cabinet pages
                break
            else :
                # Next cabinet page url extraction
                cfg['cabinet_url'] = nextCabinetPageURLExtraction(cabinet_page,\
                                                        next_page_url_pos, cfg)

    print "\nFound " + str(len(ticket_urls)) + " ticket URLs."
    return ticket_urls

def ticketURLsExtraction(page, ticket_urls_positions, cfg) :
    """
    ticketURLsExtraction(page, ticket_urls_positions)
        extracts tickets' URLs from the 'page' using its positions
        returns list of ticket URLs
    """
    ticket_urls = []
    for start_pos in ticket_urls_positions :
        end_pos = start_pos + find(page[start_pos : start_pos + 300], 
                                                    cfg['ticket_url_end_mark'])
        ticket_url = page[start_pos : end_pos]
        ticket_urls.append(ticket_url)

    return ticket_urls

def getTicketPagesByURL(http, headers, ticket_urls, cfg) :
    """
    getTicketPages(http, headers, ticket_urls)
        returns list of pages with ticket data inside
        using list of ticket URLs ('ticket_urls') from pre-authorized account
    """

    print "\nStart tickets fetching.\n"

    ticket_pages = []

    for url in ticket_urls :

        # httplib2 understands only absolute URLs
        if not url.startswith(cfg['host']) :
            url = cfg['host'] + url

        # Fetching ticket page
        response, ticket_page = http.request(url, "GET", headers = headers)

        print "\t" + url + ", status - " + response['status'] + "."

        # if page really fetched => store it
        if response['status'] == '200' :
            ticket_pages.append(ticket_page)
            
    print "\nFetched " + str(len(ticket_pages)) + " tickets from " \
                                            + str(len(ticket_urls)) + " URLs"
    
    return ticket_pages

def getTicketsPagesFromSite(cfg) :
    """
    getTicketsFromSite(login, password)
        returns list of pages with tickets from given account
    """

    # Account authentication
    http, headers = rzdAuth(cfg)

    # Get URLs of all tickets in account
    ticket_urls = getTicketURLs(http, headers, cfg)

    # Get tickets' pages ('raw_tickets')
    ticket_pages = getTicketPagesByURL(http, headers, ticket_urls, cfg)
    
    return ticket_pages

# TOOLS

def findAll(S, substring) :
    """
    Returns positions of 'substring' in 'S' as list of ints

    NB! finditer() won't find overlapping strings.
    This methods, including finditer(), find non-overlapping matches.
    To find overlapping matches you need a loop.
    """
    return [match.start() for match in finditer(escape(substring), S)]

def getList(tickets, field) :
    """
    getList(tickets, field)
        forms list of 'field' elements from list of dicts 'tickets'
        (extracts a vector from vector of dicts).
    """
    out = []
    for ticket in tickets :
        out.append(ticket[field])
    return out

def getHist(data) :
    """
    getHist(data)
        returns a histogramm of 'data' in the form of two-column table,
        sorted in descending order (1st column - quantity of each element, 
        2nd - element name). This is not a binned histogramm, 
        function only counts a quantity of each unique element.
        So, this function isn't very useful for numeric vector 
        and designed for vectors of strings.
    """
    values = []
    hist = []
    for value in data :
        if not value in values :
            values.append(value)
            hist.append(1)
        else :
            hist[values.index(value)] += 1
    out = zip(hist, values)
    out.sort(reverse = True)
    return out

# SERIALIZATION

def saveTicketPages(ticket_pages, path = './ticket_pages') :  
    """
    saveTicketPages(ticket_pages)
        write pages with ticket data inside on disk
        files format - html
        files name - md5 hash of file body
    """
    if not path[len(path) - 1] == '/' : 
        path += '/'
    for item in ticket_pages :
        filename = path + str(md5(item).hexdigest()) + '.html'
        try: 
            with open(filename, 'w') as fd : fd.write(item)
        except IOError :
            print "WARNING! Cannot save ticket page as " + filename + "!\n"
            print 'The page wouldnt be saved.\n'    
    print '\nTicket pages are saved in ' + path

def loadTicketPages(directory = './ticket_pages') :   
    """
    loadTicketPages(directory)
        load html ticket pages from 'directory'
        returns list of strings
    """
    ticket_pages = []
    print '\nLoading ticket pages from ' + directory

    try :
        for page in os.listdir(directory) :
            path = directory + '/' + page
            try: 
                with open(path, 'r') as fd : 
                    ticket_pages.append(fd.read())
            except IOError :
                print "\nWARNING! Cannot read ticket page from " + path
                print 'The page wouldnt be processed.'
            else :
                print '\t' + path
    except OSError :
        print "\nERROR! Cannot list ticket page directory " + directory
        sys.exit()
    else :
        print '\n\t' + str(len(ticket_pages)) + ' / ' \
                + str(len(os.listdir(directory))) + " files loaded."
        return ticket_pages

def saveTickets(tickets, path = './tickets.pkl') :  
    """
    saveTickets(tickets, path = './tickets.pkl')
        serialize tickets to the 'path' file
        nothing to return
    """

    while True :
        try: 
            with open(path, 'w') as fd : 
                dump(tickets, fd)
                print "\nTickets are saved as a file in " + path
            break
        except IOError :
            print "ERROR! Cannot save tickets to " + path + "!\n"
            print 'You can specify new path: '
            path = raw_input()
    

def loadTickets(path = './tickets.pkl') :   
    """
    loadTickets(path = './tickets.pkl')
        deserialize (read) tickets from the 'path' file
        returns tickets as a list of dicts
    """

    while True :
        try: 
            with open(path, 'r') as fd : 
                tickets = load(fd)
            break
        except IOError :
            print "ERROR! Cannot load tickets from " + path + "!\n"
            print 'You can specify new path: '
            path = raw_input()
            
    return tickets

def saveTable(tickets, path, cfg) :  
    """
    saveCSVTable(table, path)
        write CSV formatted 'table' on disk as 'path' file
    """
    
    while True :
        try: 
            with open(path, 'w') as fd : 
                fd.write(formTable(tickets, cfg))
                print "\nTickets are saved as a table in " + path
            break
        except IOError:
            print "ERROR! Cannot save table as " + path + "!\n"
            print 'You can specify new table locations: '
            path = raw_input()

# PARSING

def treatTextFields(tickets, cfg) :
    """
    treatTextFields(tickets) 
        treat text fields in tickets:
            - converts all string to utf8
            - makes it start with a capital letter
            - replace ugly RZD spelling of cities and stations 
                with its real ones
        returns treated tickets
    """

    # Capitalization
    fields_to_convert = ['departureCity', 'arrivalCity', 'carType', 'passenger']

    for ticket in tickets :
        for field in fields_to_convert :
            s = unicode(ticket[field], 'utf-8')
            ticket[field] = s.capitalize()

    # TODO move to config
    # Cities and Stations
    #                       Original        City                    Station
    substitution_dict = {u'Горький м'   : [u'Нижний Новогород', u'Московский вокзал)'], 
                         u'Н.новгород м': [u'Нижний Новогород', u'Московский вокзал' ],
                         u'Москва яр'   : [u'Москва',           u'Ярославский вокзал'],
                         u'Москва кур'  : [u'Москва',           u'Курский вокзал'    ],
                         u'Москва каз'  : [u'Москва',           u'Казанский вокзал'  ]}

    substitution_fields = [['departureCity', 'departureStation'], ['arrivalCity', 'arrivalStation']]

    for ticket in tickets :
        for field in substitution_fields :
            ticket[field[1]] = u'Вокзал'
            for item in substitution_dict.keys() :
                if ticket[field[0]] == item :
                    ticket[field[0]] = substitution_dict[item][0]
                    ticket[field[1]] = substitution_dict[item][1]

    return tickets

def parseTicketPages(ticket_pages, cfg) :  
    """
    parseTicketPages(ticket_pages)
        'ticket_pages' - list of string with ticket pages
        returns tickets as the list of dicts 
        according to the 'marks' settings below.
    """
    # TODO move to config
    # Marks and other stuff for parsing fucking RZD html
    # List of lists
    #         Mark,                      Start Shift,   End Shift,  Type,    Corresponding Fields of Dict
    marks = [["Ваш номер заказа",                '78', '92',       'str',   'orderNumber'],                    # 0
             ["Дата и время заказа",             '58', '79',       'date',  'orderDatetime'],                  # 1
             ["Номер поезда",                    '46', '49',       'int',   'trainNumber'],                    # 2
             ["Маршрут следования пассажира",    '77', "</td>",    'str',  ['departureCity', 'arrivalCity']],  # 3
             ["Дата и время отправления поезда", '81', '102',      'date',  'departureDatetime'],              # 4
             ["Дата и время прибытия поезда",    '75', '96',       'date',  'arrivalDatetime'],                # 5
             ["Номер вагона",                    '46', '48',       'int',   'carNumber'],                      # 6
             ["Тип вагона",                      '80', "&nbsp;",   'str',   'carType'],                        # 7
             ["Номера мест",                     '61', '63',       'int',   'seatNumber'],                     # 8
             ["Стоимость заказа",                '41', "руб.",     'int',   'price'],                          # 9
             ["ФИО",                             '  ', "&nbsp;",   'str',   'passenger']]                      # 10

    print '\nParsing ticket pages'

    # Set of orderNumbers of unique tickets
    order_numbers_set = set()

    # Parsing raw tickets
    tickets = []    # List of dicts

    #   for ticket_page in ticket_pages :
    #       ticket_page = unicode(ticket_page, 'utf-8')

    for ticket_page in ticket_pages :

        ticket = {}     # Empty Dict for coming ticket

        for mark in marks :
            # Searching for special mark that corresponds to desired data
            # Position of the mark/label
            mark_pos = find(ticket_page, mark[0])

            # Fixed length data
            if str.isdigit(mark[1]) and str.isdigit(mark[2]) :

                start_pos = mark_pos + int(mark[1])
                end_pos   = mark_pos + int(mark[2])
                chunk = ticket_page[start_pos : end_pos]

                # Converting data to non-string types
                if mark[3] == 'date' :
                    # to datetime object
                    chunk = datetime.strptime(chunk,"%d.%m.%Y&nbsp;%H:%M") 
                    # time object doesnt support subtracting  
                    #chunk = time.strptime(chunk,"%d.%m.%Y&nbsp;%H:%M")     
                    # to string 
                    #chunk = datetime.strftime("%Y.%m.%d %H:%M", chunk)      
                elif mark[3] == 'int' :
                    chunk = int(chunk)

                ticket[mark[4]] = chunk

            # Variable length data
            elif mark[0] == marks[3][0] :   # Route
                start_pos = mark_pos + int(mark[1])
                end_pos = start_pos + find(ticket_page[mark_pos \
                                    + int(mark[1]) : mark_pos + 200], mark[2])
                chunk = ticket_page[start_pos : end_pos]

                middle_pos = find(chunk, cfg['route_middle_mark'])
                #departureCity
                ticket[mark[4][0]] = chunk[0 : middle_pos]
                #arrivalCity
                ticket[mark[4][1]] = chunk[middle_pos \
                                + len(cfg['route_middle_mark']) : len(chunk)] 

            elif mark[0] == marks[7][0] :     # Car Type
                start_pos = mark_pos + int(mark[1])
                end_pos = start_pos + find(ticket_page[mark_pos + int(mark[1]) \
                                                  : mark_pos + 150], mark[2])
                chunk = ticket_page[start_pos : end_pos]
                ticket[mark[4]] = chunk

            elif mark[0] == marks[9][0] :    # Price
                start_pos = mark_pos + int(mark[1])
                end_pos = start_pos + find(ticket_page[mark_pos + int(mark[1]) \
                                                : mark_pos + 100], mark[2] ) - 9
                chunk = ticket_page[start_pos : end_pos]
                # Replacing of decimal comma with point
                # Cannot cast string '565.54' directly to int
                ticket[mark[4]] = int(float(chunk.replace(',','.')))

            elif mark[0] == marks[10][0] :    # Passenger
                # Position of the passenger's name depends on 
                # ticket price's position
                price = str(ticket['price'])
                # Too weak, price - just a three or four digit number
                price_pos = find(ticket_page, price)     
                start_pos = find(ticket_page[price_pos : price_pos + 20], \
                                cfg['passenger_end_mark']) + price_pos \
                                + len(cfg['passenger_end_mark']) 
                end_pos = start_pos + find(ticket_page[start_pos \
                                                    : start_pos + 50], mark[2])
                chunk = ticket_page[start_pos : end_pos]
                ticket[mark[4]] = chunk

            else :
                # Non-listed above field doesn't acceptable
                print "Parsing warning. Unknown field mark."

        # Uniqueness testing
        # Store only unique tickets
        if not ticket['orderNumber'] in order_numbers_set :
            order_numbers_set.add(ticket['orderNumber'])
            tickets.append(ticket)
            print "\tTicket #" + ticket['orderNumber'] + " processed"

    print '\t--------------------------------------'
    print '\t' + str(len(tickets)) + ' unique out of ' \
            + str(len(ticket_pages)) + " tickets processed."

    return  tickets

# OUTPUT

def formTable(tickets, cfg) :
    """
    formTable(tickets)
        returns printable CSV table
        'tickets' - list of dicts
    """
    # TODO move to config
    # Strong order of the fields for dictionary printing
    # List
    fields = ['orderNumber',       # 0
              'orderDatetime',     # 1
              'trainNumber',       # 2
              'departureCity',     # 3
              'departureStation',  # 4
              'arrivalCity',       # 5
              'arrivalStation',    # 6
              'departureDatetime', # 7
              'arrivalDatetime',   # 8
              'carNumber',         # 9
              'carType',           # 10
              'seatNumber',        # 11
              'price',             # 12
              'passenger']         # 13

    # Form CSV table
    delimiter = cfg['delimiter']
    table = ''
    line = ''

    # Write titles
    for field in fields :
        line = line + str(field) + delimiter

    table = table + line + '\n'

    # Write each ticket in line
    for ticket in tickets :
        line = ''
        for field in fields :  # Sorting in specific order
            chunk = ticket[field]
            if str(type(ticket[field])) == "<type 'unicode'>" :
                chunk = ticket[field].encode('utf-8', 'ignore')

            if field.endswith('Datetime') :
                chunk = datetime.strftime(ticket[field], cfg['datetime_format'])
                
            line = line + str(chunk) + delimiter

        table = table + line + '\n'

    return table

def dispTable(tickets, cfg) :
    """I can disp and save Table, but both of them need to form table before."""
    print '\n' + formTable(tickets, cfg)

def selectPassenger(tickets, name) :
    """
    selectPassenger(tickets, name) 
        returns 'tickets' filtered by passenger last 'name'
    """

    name = unicode(name, 'utf-8')
    tickets_quantity = len(tickets)
    selected_tickets = []

    print '\nPassenger selection: ' + name
    for ticket in tickets :
        if ticket['passenger'] == name :
            # 'remove' operation causes negative spillovers in treatTextFields()
            selected_tickets.append(ticket)

    if len(selected_tickets) == 0 :
        print "ERROR! There are no tickets with given passenger's name.\nExit."
        sys.exit()
    else :
        print '\tRemoved ' + str(tickets_quantity - len(selected_tickets))\
                + ' out of ' + str(tickets_quantity) + ' tickets.'
        return selected_tickets

def dispStatistics(tickets, cfg) :
    """
    dispStatistics(tickets) 
        form and display some useful descriptive statistics of ''tickets''
    """
    tickets_quantity = len(tickets) 

    def addTabs(word) :
        """ Some helpful for table formatting function """
        if len(word) < 4 :
            return '\t\t'
        elif len(word) > 7 :
            return '\t'
        else :
            return '\t\t'

    # Numbers

    print '\n\n\t┏━━━━━━━━━━━━━━━━━━━┓'
    print     '\t┃ Ticket statistics ┃'
    print     '\t┗━━━━━━━━━━━━━━━━━━━┛\n'


    print '\tTotal number of tickets: ' + str(tickets_quantity)
    print '\tYour tickets: ' + str(len(tickets)) \
            + ' (' + str( len(tickets) * 100 / tickets_quantity ) + '%)'

    # Times

    d_ord_dep = []
    d_dep_arr = []

    for ticket in tickets :
        d_ord_dep.append((ticket['departureDatetime'] \
                            - ticket['orderDatetime']).total_seconds())
        d_dep_arr.append((ticket['arrivalDatetime'] \
                            - ticket['departureDatetime']).total_seconds())
    
    # Round Coeff
    rok = 0
    
    print '\n\t\tTime differences'
    print '\t\tArr-Dep\t\tDep-Arr'
    print '----------------------------------'
    print 'Median\t\t' + str(timedelta(seconds = numpy.median(d_dep_arr))) \
              + '\t\t' + str(timedelta(seconds = numpy.median(d_ord_dep)))
    print 'Mean\t\t'   + str(timedelta(seconds = round(numpy.mean(d_dep_arr), rok))) \
              + '\t\t' + str(timedelta(seconds = round(numpy.mean(d_ord_dep), rok)))
    print 'Std\t\t'    + str(timedelta(seconds = round(numpy.std(d_dep_arr), rok))) \
              + '\t\t' + str(timedelta(seconds = round(numpy.std(d_ord_dep), rok)))
    print 'Min\t\t'    + str(timedelta(seconds = min(d_dep_arr))) \
              + '\t\t' + str(timedelta(seconds = min(d_ord_dep)))
    print 'Max\t\t'    + str(timedelta(seconds = max(d_dep_arr))) \
              + '\t\t' + str(timedelta(seconds = max(d_ord_dep)))


    # Car type
    print '\n\tCar types'
    print '-------------'
    car_types = getList(tickets, 'carType')
    car_types_zip = getHist(car_types)
    car_types_set = []
    
    for h, t in car_types_zip :
        car_types_set.append(t)
        print str(h) + '\t' + t


    # Price
    price = getList(tickets, 'price')

    # Price by car types

    # Data preparation
    price_by_car = {}

    for t in car_types_set :
        price_by_car[t] = []
        for car_type, p in zip(car_types, price) :
            if car_type == t :
                price_by_car[t].append(p)
    price_by_car['All'] = price
    car_types_set.insert(0, 'All')

    # Build Titles
    title = '\nPrices\t\t'
    for item in car_types_set :
        title += item + addTabs(item)
    title += '\n-----------------------------------------------------'

    # Build Table
    metric_function = ['median', 'mean', 'std', 'min', 'max', 'sum']
    table = title
    for metric in metric_function :
        line = metric + addTabs(metric)
        for ctype in car_types_set :
            m = str(round(getattr(numpy, metric)(price_by_car[ctype]), rok))
            line += m + addTabs(m)
        table += '\n' + line
    print table


    # Route

    routes = []
    arr_city = getList(tickets, 'arrivalCity')
    dep_city = getList(tickets, 'departureCity')


    for dc, ac in zip(dep_city, arr_city) :
        routes.append(dc + ' -> ' + ac)

    route_hist_zip = getHist(routes)
    freq, routes_set = zip(*route_hist_zip)

    price_by_route = {}
    for route in routes_set :
        price_by_route[route] = []
        for r, p in zip(routes, price) :
            if r == route :
                price_by_route[route].append(p)

    print '\n\tMedian price\tRoutes'
    print '-------------------------------'
    for freq, route in route_hist_zip :
        print str(freq) + '\t' + str(round(numpy.median(price_by_route[route]), rok))\
                + '\t\t\t' + route

    arr_stations = []
    dep_stations = []

    # Stations
    for ticket in tickets :
        if ticket['arrivalCity'] == unicode(cfg['default_city'], 'utf-8') :
            arr_stations.append(ticket['arrivalStation'])
        if ticket['departureCity'] == unicode(cfg['default_city'], 'utf-8') :
            dep_stations.append(ticket['departureStation'])

    dep_stations_zip = getHist(dep_stations)
    arr_stations_zip = getHist(arr_stations)

    print '\n\tArrival Stations'
    print '------------------------'
    for freq, value in arr_stations_zip :
        print str(freq) + '\t' + value

    print '\n\tDeparture Stations'
    print '------------------------'
    for freq, value in dep_stations_zip :
        print str(freq) + '\t' + value


# MAIN

def main(args) :
    """
    main(args)
        realize command line UI;
        to display help message use '-h'
    """
    cfg_defualt_path = './rzd-ticket-analyser.cfg'
    
    keys_help = ['-h', '--help']
    keys_acc =  ['-a', '--acc']
    keys_load = ['-l', '--load']
    keys_save = ['-s', '--save']
    keys_disp = ['-d', '--disp']
    
    program_name = args[0][2 : len(args[0])]
    
    def strKeys(k) :
        """For help message"""
        return k[0] + ' ( or ' + k[1] + ')'
        
    help_text = '\nNAME'                                                                                      \
                '\n\t' + program_name + ' provides an overview and statistics of travels by Russian Railways.' \
                                                                                                                \
                '\n\nSYNOPSIS '                                                                                  \
                '\n\t' + program_name + ' {source} [{filter}] [{output}]'                                         \
                                                                                                                   \
                '\n\nDESCRIPTION'                                                                                   \
                '\n\n\tSource of the ticket data.'                                                                   \
                '\n\t\t{source}:'                                                                                     \
                '\n\t\t\t' + strKeys(keys_acc)  + '\t\t- your RZD account;'                                            \
                '\n\t\t\t' + strKeys(keys_load) + '\tpages'   + '\t- pre-saved html-pages of tickets from your account;'\
                '\n\t\t\t\t'                    + '\ttickets' + '\t- per-serialized tickets data.'                       \
                '\n\n\tWay of output. Optional (default: display table and statistics ( = --disp all)).'                  \
                '\n\t\t{output}:'                                                                                          \
                '\n\t\t\t' + strKeys(keys_disp) + '\tstats'   + '\t- display ticket statistics;'                            \
                '\n\t\t\t\t'                    + '\ttable'   + '\t- display table of tickets;'                              \
                '\n\t\t\t\t'                    + '\tall'     + '\t- display table of ticket and statistics;'                \
                '\n\t\t\t' + strKeys(keys_save) + '\tpages'   + '\t- save ticket pages from your account in separated file;'\
                '\n\t\t\t\t'                    + '\ttickets' + '\t- save tickets in pickle file;'                         \
                '\n\t\t\t\t'                    + '\ttable'   + '\t- save table of tickets as CSV file.'                  \
                '\n\n\tOption. All the user options and most of program ones are stored in config file'                  \
                '\n\t' + cfg_defualt_path + ', in which you ought to place login and password of your RZD account. '    \
                "\n\tAlso it's avalible to set passenger's last name  for tickets' filtration or CSV table options,"   \
                "\n\tsuch as date and time format, fields' delimiter and loading/saving paths."                             \
                                                                                                                     \
                '\n\nEXAMPLES'                                                                                      \
                "\n\t" + program_name + " -a"                                                                      \
                "\n\t\t\t- get tickets from your RZD account and shows you tickets' table and statistics;"        \
                "\n\t\t\t  this is the easiest way to view numbers,"                                             \
                "\n\t\t\t  just put your login and password into "+ cfg_defualt_path + ";\n"                    \
                "\n\t" + program_name + " -l tickets -d table -s table"                                        \
                "\n\t\t\t- get tickets from pre-saved file of tickets' data, shows you tickets' table and"    \
                "\n\t\t\t  save the table as CSV file."                                                      \
                                                                                                            \
                '\n\nAUTHOR'                                                                               \
                '\n\tAndrew «ks1v» Kiselev'                                                               \
                '\n\tmail@andrewkiselev.com'                                                             \
                '\n\thttp://andrewkiselev.com'                                                          \
                '\n\thttp://twitter.com/ks1v'                                                          \
                                                                                                      \
                '\n\nREPORTING BUGS'                                                                 \
                '\n\tSubmit new issue: \thttps://bitbucket.org/ks1v/rzd-tickets-analyser/issues/new'\
                '\n\tProject repo: \t\thttps://bitbucket.org/ks1v/rzd-tickets-analyser'            \
                '\n\tProject page: \t\thttp://andrewkiselev.com/rzd-tickets-analyser'
               
    argn = len(args)
                   
    if argn == 1 :
        print 'Use -h or --help to show help.'
        sys.exit()
    
    if args[1] in keys_help :
        print help_text
        sys.exit()
        
    if argn < 2 :
        print '\nERROR! Insufficient number of arguments.'
        sys.exit()

    cfg = getConfig(cfg_defualt_path)
    checkConfig(cfg)

    if args[1] in keys_acc :
        ticket_pages = getTicketsPagesFromSite(cfg)
        tickets = parseTicketPages(ticket_pages, cfg)
        tickets = treatTextFields(tickets, cfg)
        curr_arg = 2

    elif args[1] in keys_load :
        content = args[2]
        curr_arg = 3

        if content == 'pages' :
            path = cfg['path_dir'] + cfg['path_pages']
            if not os.path.isdir(path) :
                print '\nERROR! There is no such directory like ' + path + '.'
                sys.exit()
            ticket_pages = loadTicketPages(path)
            tickets = parseTicketPages(ticket_pages, cfg)
            tickets = treatTextFields(tickets, cfg)

        elif content == 'tickets' :
            path = cfg['path_dir'] + cfg['path_tickets']
            if not os.path.isfile(path) :
                print '\nERROR! There is no such file like ' + path + '.'
                sys.exit()
            tickets = loadTickets(path)

        else :
            print '\nERROR! Unexpected content to load'
            sys.exit()
    else :
        print '\nERROR! Unexpected input action'
        sys.exit()

    if not cfg['default_passenger'] == 'any' :
        tickets = selectPassenger(tickets, cfg['default_passenger'])  

    if argn == curr_arg :
        dispTable(tickets, cfg)
        dispStatistics(tickets, cfg)
        sys.exit()

    else :

        while curr_arg < argn :

            if ( args[curr_arg] in keys_save ) and ( curr_arg + 1 <= argn ) :
                content = args[curr_arg + 1]
                curr_arg += 2
                while True :
                    try :
                        if not os.path.exists(cfg['path_dir']) : 
                            os.makedirs(cfg['path_dir'])
                        break
                    except OSError:
                        print "\nERROR! Cannot create directory for saving: " \
                                + cfg['path_dir'] + "!\n"
                        print 'You can specify new locations: '
                        cfg['path_dir'] = raw_input() 
                                                  
                if content == 'pages' :
                    if args[2] == 'tickets' :
                        print "\nWARNING! I have no ticket pages to save it."
                    else :
                        path = cfg['path_dir'] + cfg['path_pages']
                        try :
                            if not os.path.isdir(path) : 
                                os.makedirs(path)
                        except OSError :
                            print "\nWARNING! Cannot create directory: " + path
                            print 'Pages wouldnt be saved.'  
                        else :
                            saveTicketPages(ticket_pages, path)
                        continue

                elif content == 'tickets' :
                    saveTickets(tickets, cfg['path_dir'] + cfg['path_tickets'])
                    continue

                elif content == 'table' :
                    saveTable(tickets, cfg['path_dir'] + cfg['path_table'], cfg)
                    continue

                else :
                    print '\nERROR! Unexpected content to save'
                    sys.exit()

            elif ( args[curr_arg] in keys_disp ) and ( curr_arg + 2 <= argn ) :
            
                content = args[curr_arg + 1]
                curr_arg += 2
                
                if content == 'stats' :
                    dispStatistics(tickets, cfg)
                    continue

                elif content == 'table' :
                    dispTable(tickets, cfg)
                    continue

                elif content == 'all' :
                    dispTable(tickets, cfg)
                    dispStatistics(tickets, cfg)
                    continue

                else :
                    print '\nERROR! Unexpected content to display'
                    sys.exit()

            else :
                print '\nERROR! Unexpected output action'
                sys.exit()

main(sys.argv)
