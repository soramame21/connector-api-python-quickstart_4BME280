import mbed_connector_api                 # mbed Device Connector library
import pybars                             # use to fill in handlebar templates
from   flask             import Flask    # framework for hosting webpages
from   flask_socketio     import SocketIO, emit,send,join_room, leave_room
from   base64             import standard_b64decode as b64decode
import os

app = Flask(__name__)
socketio = SocketIO(app,async_mode='threading')

if 'ACCESS_KEY' in os.environ.keys():
    token = os.environ['ACCESS_KEY'] # get access key from environment variable
else:
    token = "ChangeMe" # replace with your API token

connector = mbed_connector_api.connector(token)

@app.route('/')
def index():
    # get list of endpoints, for each endpoint get the pattern (/3201/0/5853) value
    epList = connector.getEndpoints().result
    for index in range(len(epList)):
        print "ren01 Endpoint Found: ",epList[index]['name']
        print "ren01 epList[index]", epList[index]
        print "end ren01", index
        e_h = connector.getResourceValue(epList[index]['name'],"/3304/0/5700")
        e_t = connector.getResourceValue(epList[index]['name'],"/3303/0/5700")
        e_p = connector.getResourceValue(epList[index]['name'],"/3323/0/5700")
        while not e_p.isDone() or not e_t.isDone or not e_h.isDone :
            None
        epList[index]['humidity_value'] = e_h.result
        epList[index]['tempereture_value'] = e_t.result
        epList[index]['pressure_value'] = e_p.result
    print "Endpoint List :",epList
    # fill out html using handlebar template
    handlebarJSON = {'endpoints':epList}
    comp = pybars.Compiler()
    tmp_src = open("./views/index.hbs",'r').read()
    source = unicode(tmp_src, "utf-8")
    template = comp.compile(source)
    return "".join(template(handlebarJSON))

@socketio.on('connect')
def connect():
    print('connect ')
    join_room('room')

@socketio.on('disconnect')
def disconnect():
    print('Disconnect')
    leave_room('room')

@socketio.on('subscribe_to_presses')
def subscribeToPresses(data):
    print('222 subscribe_to_presses: ',data)
    # Subscribe to all changes of resource /3303/0/5700 (button presses)
    e_h = connector.putResourceSubscription(data['endpointName'],'/3304/0/5700')
    e_t = connector.putResourceSubscription(data['endpointName'],'/3303/0/5700')
    e_p = connector.putResourceSubscription(data['endpointName'],'/3323/0/5700')
    while not e_h.isDone() or not e_t.isDone() or not e_p.isDone():
        None
    if e_h.error:
        print("Error e_h 21: ",e_h.error.errType, e_h.error.error, e.raw_data)
    elif e_t.error:
        print("Error e_t 21: ",e_t.error.errType, e_t.error.error, e_t.raw_data)
    elif e_p.error:
        print("Error e_p 21: ",e_p.error.errType, e_p.error.error, e_p.raw_data)
    else:
        print("Subscribed Successfully!")
        emit('subscribed-to-presses')

@socketio.on('unsubscribe_to_presses')
def unsubscribeToPresses(data):
    print('unsubscribe_to_presses: ',data)
    e_h = connector.deleteResourceSubscription(data['endpointName'],'/3304/0/5700')
    e_t = connector.deleteResourceSubscription(data['endpointName'],'/3303/0/5700')
    e_p = connector.deleteResourceSubscription(data['endpointName'],'/3323/0/5700')
    while not e_h.isDone() or not e_t.isDone() or not e_p.isDone():
        None
    if e_h.error:
        print("Error e_h 22: ",e_h.error.errType, e_h.error.error, e.raw_data)
    elif e_t.error:
        print("Error e_t 22: ",e_t.error.errType, e_t.error.error, e_t.raw_data)
    elif e_p.error:
        print("Error e_p 22: ",e_p.error.errType, e_p.error.error, e_p.raw_data)
    else:
        print("Unsubscribed Successfully!")
    emit('unsubscribed-to-presses',{"endpointName":data['endpointName'],"value":'True'})

@socketio.on('get_presses')
def getPresses(data):
    # Read data from GET resource /3200/0/5501 (num button presses)
   # print("ren02>,  get_presses ",data)
    e_h = connector.getResourceValue(data['endpointName'],"/3304/0/5700")
    e_t = connector.getResourceValue(data['endpointName'],"/3303/0/5700")
    e_p = connector.getResourceValue(data['endpointName'],"/3323/0/5700")
    while not e_p.isDone() or not e_t.isDone or not e_h.isDone :
        None
    if e_h.error :
        print("Error e_h: ",e_h.error.errType, e_h.error.error, e_h.raw_data)
    elif e_t.error :
        print("Error e_t: ",e_t.error.errType, e_t.error.error, e_t.raw_data)
    elif e_p.error :
        print("Error e_p: ",e_p.error.errType, e_p.error.error, e_p.raw_data)
    else:
        dataT_to_emit = {"endpointName":'multiple_data', "value":"e_t="+e_t.result+";e_h="+e_h.result+";e_p="+e_p.result}
        emit('SetTemp', dataT_to_emit)


# 'notifications' are routed here, handle subscriptions and update webpage
def notificationHandler(data):
    global socketio

    print "\r\nNotification Data Received : %s" %data['notifications']
    notifications = data['notifications']
    tmp=""
    for thing in notifications:
        if  thing["path"]=="/3304/0/5700":  tmp +="e_h="+b64decode(thing["payload"])+";"
        elif thing["path"]=="/3303/0/5700":  tmp +="e_t="+b64decode(thing["payload"])+";"
        elif thing["path"]=="/3323/0/5700":  tmp +="e_p="+b64decode(thing["payload"])+";"
    stuff = {"endpointName":thing["ep"],"value":tmp+"end"}
    print ("990 Emitting :",stuff)
    socketio.emit('SetTemp',stuff)

if __name__ == "__main__":
    connector.deleteAllSubscriptions()                            # remove all subscriptions, start fresh
    connector.startLongPolling()                                # start long polling connector.mbed.com
    connector.setHandler('notifications', notificationHandler)     # send 'notifications' to the notificationHandler FN
    socketio.run(app,host='0.0.0.0', port=8080)
