#####   IMPORTS   #####
# Internet
from werkzeug.serving import WSGIRequestHandler
from flask import Flask, request	# Requires pip3 install flask
from pynat import get_ip_info		# Requires pip3 install pynat
import requests 					# Requires pip install requests
import socket

# Multi thread/process
import time
import threading
from multiprocessing import Process, Queue, Value, Array
import signal

# System, files
import os, sys, platform
import loader				# In project directory
import logging

# Basic
import random, string, builtins
import json



#####   GLOBAL VARIABLES   #####

# Identifier of this agent
my_agent_ID = None

# Identifier of the project that this agent belongs to
my_project_folder = None

# Indicator of verbosity or silent mode
verbose = False

# Indicator of logginng level (to file)
#log_to_file = False

# Dictionary of agents 
cloudbook_dict_agents = {}

# List of deployable units that this agent has to load
du_list = []

# Dictionary of agent configuration
agent_config_dict = {}

# Dictionary of circle configuration
configjson_dict = {}

# Index in order to make the round robin assignation of invocation requests
round_robin_index = 0

# FIFO queue that passes stats to the stats file creator thread
mp_stats_queue = None

# Global variable to store the general path to cloudbook, used to access all files and folders needed
if platform.system()=="Windows":
	cloudbook_path = os.environ['HOMEDRIVE'] + os.environ['HOMEPATH'] + os.sep + "cloudbook"
else:
	cloudbook_path = os.environ['HOME'] + os.sep + "cloudbook"

# Path to the project the agent belongs to
project_path = None

# Path to the distributed filesystem
fs_path = None

# Variable that contains the information from agents_grant.json (last read)
#Format:
# {
# 	"agent_0": {"GRANT": "LOW", "IP": "192.168.1.44", "PORT": 5000},
# 	"agent_G2UQXFV1O2NWTNRQY8GD": {"GRANT": "LOW", "IP": "192.168.1.44", "PORT": 5001},
# 	"agent_IGPAMITGCCPPYMTQ4BQA": {"GRANT": "LOW", "IP": "192.168.1.44", "PORT": 5002},
# 	"agent_OMRZ22CQB157H3POXG3A": {"GRANT": "LOW", "IP": "192.168.1.44", "PORT": 5003}
# }
agents_grant = {}

# Global variable with the list of deployable units that have already been loaded
loaded_du_list = []

# Number of times the cloudbook has changed and DUs have been (re)loaded
cloudbook_version = 0



#####   CONSTANTS   #####
CRIT_ERR_NO_ANSWER = "CLOUDBOOK CRITICAL ERROR: no agent could answer the remote invocation to a function in a critical DU. \
The DU state is lost and program is corrupt. Critical alarm created in the distributed filesystem in order that deployer's \
surveillance monitor knows that an invocation has failed. The Flask process will be stopped and restarted."
ERR_IP_NOT_FOUND = "ERROR: cannot find the ip and port for invoking the desired agent."
ERR_QUEUE_KEY_VALUE = "ERROR: there was a problem item obtained from the queue. Wrong key/value."
ERR_READ_WRITE = "ERROR: reading/writing not allowed or wrong path."
ERR_FLASK_PORT_IN_USE = "ERROR: this agent is using a port that was checked to be free but, due to race conditions, another \
agent did the same and started using it before."
ERR_DUS_NOT_EXIST = "ERROR: cannot load the specified DU(s), because file(s) do not exist."
GEN_ERR_LAUNCHING_FLASK = "GENERIC ERROR: something went wrong when launching the flask thread."
GEN_ERR_LOADING_DUS = "GENERIC ERROR: something went wrong when loading DUs."
ERR_DUS_ALREADY_LOADED = "ERROR: a list of DU(s) has already been loaded."
ERR_NO_LAN = "ERROR: the local IP was not found. The device is not connected to internet nor any LAN."
ERR_NO_INTERNET = "ERROR: external IP or port not found. Either the device is not conected to the internet or the STUN server \
did not accept the request."
GEN_ERR_RESTARTING_FLASK = "GENERIC ERROR: something went wrong when restarting the flask process."
GEN_ERR_INIT_CHECK_FLASK = "GENERIC ERROR: something went wrong when initializing of checking that FlaskProcess was up and \
running correctly."
ERR_GET_PROJ_ID_REFUSED = "ERROR: conection refused when FlaskProcess was trying to check the id of the agent running on the \
requested port."
ERR_LOAD_CRIT_DU_CLOUDBOOK_RUNNING = "ERROR: cloudbook is already running and critical dus should not be loaded at this \
point in order to avoid unexpected behaviours due to global variables may have lost their state."
ERR_NO_JSONIZABLE = "ERROR: cannot convert the invocation parameters into json."
ERR_NO_JSON_RESPONSE = "ERROR: there was not json information in the response."

COMMAND_SYNTAX = "\
 ____________________________________________________________________________________________________________ \n\
|                                                                                                            |\n\
| SYNTAX:                                                                                                    |\n\
|   agent.py -agent_id <agent_id> -project_folder <project_folder> [-verbose] [-help|-syntax|-info]          |\n\
|                                                                                                            |\n\
| EXAMPLE:                                                                                                   |\n\
|   agent.py -agent_id agent_S4MY6ZGKQRT8RTVWLJZP -project_folder NBody -verbose                             |\n\
|                                                                                                            |\n\
| OPTIONS:                                                                                                   |\n\
|   Mandatory:                                                                                               |\n\
|     -agent_id <agent_id>                <agent_id> is the name of the agent to launch.                     |\n\
|     -project_folder <project_folder>    <project_folder> is the name of the folder containing the agent.   |\n\
|                                                                                                            |\n\
|   Optional:                                                                                                |\n\
|     -verbose                            This option will make the agent print cloudbook information.       |\n\
|     -help, -syntax, -info               This option will print this help and syntax info and terminate.    |\n\
|                                                                                                            |\n\
| Note: the order of the options is not relevant. Unrecognized options will be ignored.                      |\n\
|____________________________________________________________________________________________________________|"



#####   OVERLOAD BUILT-IN FUNCTIONS   #####

# Print function overloaded in order to make it print the id before anything and keep track of the traces of each agent easier.
def print(*args, **kwargs):
	# If the print is just a separation, i.e.:  print()  keep it like that
	if (len(args)==0 and len(kwargs)==0) or (len(args)==1 and len(kwargs)==0 and args[0]==''):
		builtins.print()
		return

	# If the agent ID has been already set
	if my_agent_ID is not None:
		if verbose:
			if my_agent_ID == "agent_0": 	# For the agent_0 add dots to make it start at the same letter column in the console
				builtins.print(my_agent_ID + "...................:", *args, **kwargs)
			else:
				builtins.print(my_agent_ID + ":", *args, **kwargs)
		else:
			pass
	else: 	# For the case in which the ID is None, print it with the normal built-in
		builtins.print(*args, **kwargs)



#####   APPLICATION TO SEND AND RECEIVE FUNCTION REQUESTS   #####

# Global variable that stores the Flask app (used in the decorators)
application = Flask(__name__)

# This function is only for testing purposes. Returns "Hello"
@application.route("/", methods=['GET', 'PUT', 'POST'])
def hello():
	print("Hello world")
	return "Hello"


# This function returns a concatenaion of the project and agent_id which is running the server
@application.route("/get_project_agent_id", methods=['GET', 'PUT', 'POST'])
def get_project_agent_id():
	print("/get_project_agent_id route has been invoked.")
	return json.dumps(my_project_folder + " - " + my_agent_ID)

# @application.route('/quit')
# def flask_quit():
# 	func = request.environ.get('werkzeug.server.shutdown')
# 	print(request.environ)
# 	func()
# 	print("/quit route has been invoked.")
# 	return "Quitting..."


# This function receives and executes invocations from other agents. Requires a json dictionary with the information to invoke the function.
@application.route("/invoke", methods=['GET','POST'])
def invoke(configuration = None):
	global du_list
	global my_agent_ID
	global stats_dict

	print("=====AGENT: /INVOKE=====")
	print("Thread ID:", threading.get_ident())
	invoked_data = ""
	params = None

	request_data = request.get_json()
	# If the json content exists (new format of request)
	if request_data is not None:
		print("This request has the new format with JSON")
		print("REQUEST.json:", request_data)

		if "invoker_function" in request_data:
			invoker_function = request_data["invoker_function"]
		if "invoked_function" in request_data:
			invoked_function = request_data["invoked_function"]
		if "invoked_du" in request_data:
			invoked_du = request_data["invoked_du"]
		if "params" in request_data:
			params = request_data["params"]

	# If the json content does not exist (old format of request) ############ DELETE (se queda de momento para el deployer_run)###########
	else:
		print("This request has the old format")
		print("REQUEST.form: ", request.form)
		du_and_invoked_function = request.args.get('invoked_function') 			# Must always exist
		invoker_function = request.args.get('invoker_function', None) 			# Defaults to None if it does not exist
		
		(invoked_du, invoked_function) = du_and_invoked_function.split(".") 	# Separate du and function

		for i in request.form:
			invoked_data = i

		print("invoked_du:", invoked_du)
		print("invoked_function:", invoked_function)
		print("invoker_function:", invoker_function)
		print("invoked_data:", invoked_data)

		print("du_list:", du_list)

		#raise Exception("Old invocation syntax is now not supported")
		# Queue data stats
		stats_data = {}
		stats_data['invoked'] = invoked_function
		stats_data['invoker'] = invoker_function
		mp_stats_queue.put(stats_data)

		# If the function belongs to the agent
		if invoked_du in du_list:
			while invoked_du not in loaded_du_list:
				print("The function belongs to the agent, but it has not been loaded yet.")
				time.sleep(1)

			if "%3d" in invoked_data:
				invoked_data = invoked_data.replace("%3d","=")
			try:
				eval_result = eval(invoked_du+"."+invoked_function+"("+invoked_data+")")
			except:
				eval_result = eval(invoked_du+"."+invoked_function+"('"+invoked_data+"')")
		# If the function does not belong to this agent
		else:
			print("This function does not belong to this agent.")
			eval_result = "none"

		return eval_result if eval_result is not None else ""
		################################## OLD REQUEST FORMAT END ##############################################

	# Print the data obtained from the request (and du_list)
	print("Invocation dictionary:", "\n", 				\
		"  invoked_du", invoked_du, "\n", 				\
		"  invoked_function", invoked_function, "\n", 	\
		"  invoker_function", invoker_function, "\n", 	\
		"  params", params, "\n"						\
		)

	# Check parameters
	assert invoked_du is not None 			# Must exist
	assert invoked_function is not None 	# Must exist
	assert params is not None 				# Must exist
	assert params["args"] is not None 		# Must exist, may be empty list
	assert params["kwargs"] is not None 	# Must exist, may be empty dictionary

	# Queue data stats
	stats_data = {}
	stats_data['invoked'] = invoked_function
	stats_data['invoker'] = invoker_function
	mp_stats_queue.put(stats_data)

	# If the function belongs to the agent
	if invoked_du in du_list:
		while invoked_du not in loaded_du_list:
			print("The function belongs to the agent, but it has not been loaded yet.")
			time.sleep(1)

		# Create command and eval
		command_to_eval = invoked_du + "." + invoked_function + "(*params['args'], **params['kwargs'])"
		print("Command to evaluate is:\t", command_to_eval)
		eval_result = eval(command_to_eval)
		print("Response:", eval_result)

	# If the function does not belong to this agent
	else:
		print("This function does not belong to this agent.")
		eval_result = "none"

	return eval_result


# This function replaces the "invoker" function of each du and allows to send invoke requests to other agents (or invoke itself if possible).
# Requires a dictionary with the information to invoke the function.
def outgoing_invoke(invocation_dict, configuration = None):
	global round_robin_index

	# Internal function to write alarms (files). Parameter is the importance level (the alarm file name)
	def write_alarm(alarm_name):
		(hot_redeploy, cold_redeploy) = check_redeploy_files()
		if not hot_redeploy and not cold_redeploy: 	# Only do something if there are no redeployment files
			possible_alarms = ["CRITICAL", "WARNING"]
			assert alarm_name in possible_alarms
			alarm_file_path = fs_path + os.sep + alarm_name
			open(alarm_file_path, 'a').close() 	# Create an alarm file if it does not exist
			print(alarm_name, " alarm file has been created.")
		else:
			print("Alarm not created due to the existence redeployment files.")

	print("=====AGENT: OUTGOING_INVOKE=====")
	print("Thread ID: ", threading.get_ident())

	# Get items from the dict
	try:
		invoked_du 			= invocation_dict["invoked_du"]
		invoked_function 	= invocation_dict["invoked_function"]
		invoker_function 	= invocation_dict["invoker_function"]
		params 				= invocation_dict["params"]
	except:
		raise Exception("Keys missing")

	print("Invocation dictionary:", "\n", 				\
		"  invoked_du", invoked_du, "\n", 				\
		"  invoked_function", invoked_function, "\n", 	\
		"  invoker_function", invoker_function, "\n", 	\
		"  params", params, "\n"						\
		)

	# Check parameters
	assert invoked_du is not None 			# Must exist
	assert invoked_function is not None 	# Must exist
	assert params is not None 				# Must exist
	assert params["args"] is not None 		# Must exist, may be empty list
	assert params["kwargs"] is not None 	# Must exist, may be empty dictionary

	# If the du is in this agent (du_default is special case, it does not count), then it is a local invocation
	if invoked_du in du_list and invoked_du != 'du_default':
		print("===AGENT: LOCAL INVOCATION===")

		# Create command and eval
		command_to_eval = invoked_du + "." + invoked_function + "(*params['args'], **params['kwargs'])"
		print("Command to evaluate is:\t", command_to_eval)
		eval_result = eval(command_to_eval)
		print("Response:", eval_result)

		# Queue data stats
		stats_data = {}
		stats_data['invoked'] = invoked_function
		stats_data['invoker'] = invoker_function
		mp_stats_queue.put(stats_data)

		try:
			return eval(eval_result)
		except:
			return eval_result

	# If the du is not in the agent
	# Get the possible agents to invoke
	global my_agent_ID
	list_agents = list(cloudbook_dict_agents.get(invoked_du)) # Agents containing the DU that has the function to invoke

	# Get the version of the cloudbook in order to check for changes
	invocation_cloudbook_version = cloudbook_version

	invocation_agents_grant = agents_grant

	# Get the agents to invoke
	invocation_agents_list = list_agents[round_robin_index:len(list_agents)] + list_agents[0:round_robin_index]
	last_agent = invocation_agents_list[-1] 	# -1 indicates the last element of the list

	i = 0
	while i < len(list_agents):
		remote_agent = invocation_agents_list[i]
		print("The selected remote agent to invoke is: ", remote_agent, " from list ", list_agents, " rewritten as ", invocation_agents_list)

		# Update round robin index
		if len(list_agents) > 1:
			round_robin_index = (round_robin_index+1) % len(list_agents)
			print("round_robin_index = ", round_robin_index)
		try:
			desired_host_ip_port = invocation_agents_grant[remote_agent]['IP'] + ":" + str(invocation_agents_grant[remote_agent]['PORT'])
			print("Host ip and port: ", desired_host_ip_port)
		except Exception as e:
			print(ERR_IP_NOT_FOUND)
			raise e 	# This should never happen

		url = "http://"+desired_host_ip_port+"/invoke"
		print("Launching post to:", url, "with data:", invocation_dict)

		try:
			r = get_session().post(url, json=invocation_dict)
			break	# Stop iterating over the possible agents (already got a responsive one)
		except TypeError as e:
			print(ERR_NO_JSONIZABLE)
			raise e
		except Exception as e:
			print("POST request was not answered by " + remote_agent + " (IP:port --> " + desired_host_ip_port + ")")
			print(e)
			write_alarm("WARNING")

			if remote_agent == last_agent: 	# If all agents have been tested
				print("No agents available to execute the requested function.")
				if is_critical(invoked_du): 	# If the du is critical
					print("The function that could not be invoked is in a critical du: ", invoked_du + "." + invoked_function)
					write_alarm("CRITICAL")
					while True:
						time.sleep(1)
						print("This agent has detected a problem and will be automatically restarted.")
					# raise BaseException(CRIT_ERR_NO_ANSWER)
				else: 	# If the du is NOT critical
					print("The function that could not be invoked is in a NON-critical du: ", invoked_du + "." + invoked_function)
					
					# Wait until new cloudbook version is charged
					while invocation_cloudbook_version == cloudbook_version:
						print("Waiting for redeployment to reallocate " + invoked_du + " in an accessible agent.")
						time.sleep(1)
					
					# Refresh the variables after the hot redeployment in order to try again
					list_agents = list(cloudbook_dict_agents.get(invoked_du))
					invocation_cloudbook_version = cloudbook_version
					invocation_agents_grant = agents_grant
					invocation_agents_list = list_agents[round_robin_index:len(list_agents)] + list_agents[0:round_robin_index]
					last_agent = invocation_agents_list[-1]
					i = 0
					print("Retrying with new cloudbook...")

			else: 	# If there are still agents to try
				print("Retrying...")
				i += 1
		# end_of_except
	# end_of_while
		
	# If the loop finishes with break, then a response has been received and this invocation and function finishes normally.
	try:
		readed_response = r.json()
	except Exception as e:
		print(ERR_NO_JSON_RESPONSE)
		raise e
	print("Response received:", readed_response)

	try: 		# For functions that return some json
		data = readed_response.decode()
		aux = eval(data)
	except: 	# For other data types
		aux = readed_response
	return aux



#####   ARRAYS AND VALUES HANDLING AND TRANSFORMATION FUNCTIONS   #####

# This function puts a string into a multiprocesssing array and fills the extra array slots with "\x00".
# Note: internally converts the string into an array of binary utf-8 encoded characters.
# If the string does not fit in the array, exception is raised.
def string2array(str_var, arr_var):
	with arr_var.get_lock():
		arr_len = len(arr_var)
		str_len = len(str_var)
		if str_len>arr_len:
			raise Exception("The string is longer than the array.")
		else:
			equal_length_string = str_var + "".join("\x00" for _ in range(arr_len - str_len))
			arr_var.value = equal_length_string.encode("utf-8")


# This function takes a multiprocesssing array and returns its value as a normal string.
# Note: internally converts the array of binary utf-8 encoded characters back to string.
def array2string(arr_var):
	with arr_var.get_lock():
		return arr_var.value.decode("utf-8")


# This function takes a grant string and returns it transformed into a number.
def grant2num(grant):
	if grant=="LOW":
		return 1
	if grant=="MEDIUM":
		return 2
	if grant=="HIGH":
		return 3
	return 0


# This function takes a number and returns it transformed into a grant string.
def num2grant(num):
	if num==1:
		return "LOW"
	if num==2:
		return "MEDIUM"
	if num==3:
		return "HIGH"
	return ""


# This function takes a number and puts it into a multiprocessing value.
def num2value(num, val_var):
	with val_var.get_lock():
		val_var.value = num


# This function takes a multiprocessing value and returns its value as number.
def value2num(val_var):
	with val_var.get_lock():
		return val_var.value



#####   AGENT FUNCTIONS   #####

# Function handler of the Ctrl+C event
def sigint_handler(*args):
	try:
		flask_proc.terminate()
	except Exception as e:
		pass
	os._exit(0)


# This function returns a dictionary containing all the information of the agent and circle that may be useful for a programmer
# that uses cloudbook in order to make a program that behaves differently depending on Cloudbook internal information.
def __CLOUDBOOK__():
	programmer_accessible_dict = {}
	programmer_accessible_dict["agent"] = {}
	programmer_accessible_dict["agent"]["grant"] = num2grant(value2num(value_var_grant))
	programmer_accessible_dict["agent"]["ip"] = array2string(array_var_ip)
	programmer_accessible_dict["agent"]["port"] = value2num(value_var_port)
	programmer_accessible_dict["agent"]["id"] = my_agent_ID

	programmer_accessible_dict["circle"] = {}
	programmer_accessible_dict["circle"]["num_available_agents"] = len(agents_grant)
	programmer_accessible_dict["circle"]["agents_grant"] = agents_grant # dict(Keys: agent ids. Values: dicts(Keys: "GRANT", "IP" and "PORT"))

	return programmer_accessible_dict


# This function is used by the GUI. Generates a new agent given the grant level and the FS (if provided)
# Checks the OS to adapt the path of the folders.
# Generates a default configuration file that is edited and adapted afterwards.
def create_agent(grant, project_name, fs=False, agent_0=False):

	# Check paths existence and create if they do not.
	if not os.path.exists(cloudbook_path):
		os.makedirs(cloudbook_path)
	
	poject_path = cloudbook_path + os.sep + project_name
	if not fs:
		fs = poject_path + os.sep + "distributed"
	if not os.path.exists(fs):
		os.makedirs(fs)

	# Create dictionary with the agent info
	agent_config_dict = {} # = {"AGENT_ID": "0", "GRANT_LEVEL": "MEDIUM", "DISTRIBUTED_FS": fs+"/distributed"}
	if agent_0:
		id_num = 0
	else:
		id_num = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
	agent_ID = "agent_" + str(id_num)
	agent_config_dict['AGENT_ID'] = agent_ID
	agent_config_dict['GRANT_LEVEL'] = grant
	agent_config_dict['DISTRIBUTED_FS'] = fs

	# Write dictionary in file
	config_file_path = poject_path + os.sep + "agents" + os.sep + "config_"+agent_ID+".json"
	loader.write_dictionary(agent_config_dict, config_file_path)

	print("\n---  NEW AGENT CREATED  ----------------------------------------------------------------------------")
	print("     Agent_id = ", id_num)
	print("     Grant    = ", grant)
	print("     FSPath   = ", fs)
	print("----------------------------------------------------------------------------------------------------\n")


# This function is used by the GUI. Modifies the the grant level and/or the FS of the current agent according to the parameters given.
def edit_agent(agent_id, project_name, new_grant='', new_fs=''):
	if new_grant=='' and new_fs=='':
		return

	config_agent_file_path = cloudbook_path + os.sep + project_name + os.sep + "agents" + os.sep + "config_"+agent_id+".json"
	config_dict = loader.load_dictionary(config_agent_file_path)

	if new_grant!='' and new_grant!=None:
		config_dict["GRANT_LEVEL"] = new_grant

	if new_fs!='' and new_fs!=None:
		config_dict["DISTRIBUTED_FS"] = new_fs

	loader.write_dictionary(config_dict, config_agent_file_path)


# This function launches the flask server in the port given as parameter.
def flaskThreaded(port, sock=None):
	port = int(port)
	print("Launching in port:", port)
	if not verbose:
		os.environ['WERKZEUG_RUN_MAIN'] = 'true'
	if sock:
		sock.close()
	application.run(debug=False, host="0.0.0.0", port=port, threaded=True)
	# import psutil
	# num_cores = psutil.cpu_count()
	# print("The number of cores of the machine is:", num_cores)
	# application.run(debug=False, host="0.0.0.0", port=port, threaded=False, processes=num_cores)
	# global first_launch
	# first_launch = False
	print("00000000000000000000000000000000000000000000000000000000000000000000000000")


# This function gets the global session object (creates it if it does not exist yet)
def get_session():
	global session
	if not session:
		session = requests.Session()
	return session


# This function is used in a new process. It is in charge of handling the queues for data exchange (and load DUs) to allow Flask execution.
def flaskProcessFunction(mp_agent2flask_queue, mp_flask2agent_queue, mp_stats_queue_param,\
						stdin_stream, value_var_grant_param, array_var_ip_param, value_var_port_param):
	global mp_stats_queue
	mp_stats_queue = mp_stats_queue_param
	global value_var_grant
	value_var_grant = value_var_grant_param
	global array_var_ip
	array_var_ip = array_var_ip_param
	global value_var_port
	value_var_port = value_var_port_param
	# NOT USED globals: configjson_dict, agent_config_dict
	# NOT MODIFIED globals: cloudbook_path, round_robin_index

	# Note: this global variables belong to other process
	# init_info vars:
	global my_agent_ID
	global my_project_folder
	global fs_path
	global verbose
	global project_path
	start_port_search = 5000

	# launch vars:
	global session 			# HTTP session used to launch/receive all conections (using only one port)
	session = None
	get_session()
	flask_thread = None

	# deploy_info vars:
	global cloudbook_dict_agents
	global agents_grant
	global cloudbook_version
	global du_list
	global loaded_du_list

	# local_port = None
	# global first_launch
	# first_launch = True
	while True:
		while not mp_agent2flask_queue.empty():
			item = mp_agent2flask_queue.get()
			
			if "init_info" in item:
				try:
					my_agent_ID 		= item["init_info"]["my_agent_ID"]
					my_project_folder 	= item["init_info"]["my_project_folder"]
					fs_path 			= item["init_info"]["fs_path"]
					start_port_search 	= item["init_info"]["start_port_search"]
					verbose 			= item["init_info"]["verbose"]

					project_path = cloudbook_path + os.sep + my_project_folder
				except Exception as e:
					print(ERR_QUEUE_KEY_VALUE)
					raise e

				# Allow input from console
				sys.stdin = os.fdopen(stdin_stream)

				# Add the path
				sys.path.append(fs_path + os.sep + "working_dir")

			elif "launch_info" in item:
				try:
					launch 				= item["launch_info"]
					cold_redeploy 		= item["launch_info"]["cold_redeploy"]
				except Exception as e:
					print(ERR_QUEUE_KEY_VALUE)
					raise e
				try:
					WSGIRequestHandler.protocol_version = "HTTP/1.1"
					if not cold_redeploy:
						(local_port, sock) = get_port_available(port=start_port_search)
						flask_thread = threading.Thread(target=flaskThreaded, args=[local_port, sock], daemon=True)
					else:
						local_port = start_port_search
						flask_thread = threading.Thread(target=flaskThreaded, args=[local_port], daemon=True)
					flask_thread.start()

					# Set up the werkzeug logger
					werkzeug_logger = logging.getLogger('werkzeug')
					werkzeug_logger.setLevel(logging.ERROR)
					if not verbose:
						werkzeug_logger.disabled = True
						application.logger.disabled = True

					retrieved_project_id = None
					while not retrieved_project_id:
						try:
							resp = get_session().get("http://localhost:"+str(local_port)+"/get_project_agent_id")#, headers={'Connection':'close'})
						except Exception as e:
							print(ERR_GET_PROJ_ID_REFUSED)
						try:
							retrieved_project_id = resp.json()
							break
						except:
							print(ERR_NO_JSON_RESPONSE)
							retrieved_project_id = None
						time.sleep(0.5)
						print("Retrying...")

					mp_queue_data = {}
					if my_project_folder + " - " + my_agent_ID == retrieved_project_id:
						mp_queue_data["flask_proc_ok"] = {}
						mp_queue_data["flask_proc_ok"]["local_port"] = local_port
					else:
						print(ERR_FLASK_PORT_IN_USE) # This is the 2nd flask in the same port (race conditions)
						print("The flask process will be restarted automatically.")
						mp_queue_data["restart_flask_proc"] = ERR_FLASK_PORT_IN_USE
					mp_flask2agent_queue.put(mp_queue_data)
					cloudbook_version = 1
				except Exception as e:
					print(GEN_ERR_LAUNCHING_FLASK)
					raise e

			elif "deploy_info" in item:
				try:
					cloudbook_dict_agents 	= item["deploy_info"]["cloudbook_dict_agents"]
					agents_grant 			= item["deploy_info"]["agents_grant"]
					new_du_list 			= item["deploy_info"]["new_du_list"]
					cloudbook_version += 1
				except Exception as e:
					print(ERR_QUEUE_KEY_VALUE)
					raise e

				# Load the dus that could not be loaded and the new ones, if any
				not_loaded_du_list = [du for du in new_du_list if du not in loaded_du_list]
				if not_loaded_du_list:
					# Update du_list (but use only old_du_list and new_du_list to have clean code)
					old_du_list = du_list
					du_list = new_du_list
					print("old_du_list:", old_du_list)
					print("new_du_list:", new_du_list)
					print("The currently loaded DUs are:", loaded_du_list)
					print("The following DUs will be loaded now:", not_loaded_du_list)

					try:
						du_files_path = fs_path + os.sep + "du_files"
						sys.path.append(du_files_path)
						for du in not_loaded_du_list:
							print("  Trying to load", du)
							if is_critical(du) and cloudbook_is_running():
								print("  ", ERR_LOAD_CRIT_DU_CLOUDBOOK_RUNNING)
								print("  ", du, "has been skipped (not loaded)")
								continue
							du_i_file_path = du_files_path + os.sep + du+".py"
							while not os.path.exists(du_i_file_path):
								print(ERR_DUS_NOT_EXIST)
								time.sleep(1)
							exec("global "+du, globals())
							exec("import "+du, globals())
							exec(du+".invoker=outgoing_invoke")
							exec(du+".__CLOUDBOOK__=__CLOUDBOOK__")
							print("  ", du, "successfully loaded")
							loaded_du_list.append(du)

						print("The currently loaded DUs are:", loaded_du_list)
						if all([du in loaded_du_list for du in new_du_list]):
							print("All DUs have been loaded successfully.")
						else:
							print("Not all DUs could be loaded.")

					except Exception as e:
						print(GEN_ERR_LOADING_DUS)
						raise e
				else:
					print("There are no new DUs to load.")

			else:
				print(ERR_QUEUE_KEY_VALUE)

		time.sleep(1)


# Target function of the stats file creator thread. Implements the consumer of the producer/consumer model using mp_stats_queue.
def create_stats(t1):
	print("Stats creator thread started")
	time_start = time.monotonic()
	stats_dictionary = {}
	stats_file_path = project_path + os.sep + "distributed" + os.sep + "stats" + os.sep + "stats_"+my_agent_ID+".json"

	while True:
		current_time = time.monotonic()
		while not mp_stats_queue.empty():
			item = mp_stats_queue.get()
			#print("New stat: ", item)

			# Add data to dictionary
			try:
				invoker = item['invoker']
				invoked = item['invoked']
			except:
				print(ERR_QUEUE_KEY_VALUE, "Stats queue needs invoker/invoked keys.")

			try:
				if invoker != None:
					stats_dictionary[invoked][invoker] += 1 	# Add 1 to the existing dictionary entry
			except:
				if invoker != None:
					try: 
						stats_dictionary[invoked][invoker] = 1  # Key 'invoker' not in the 'invoked' dictionary --> create and set to 1
					except:
						stats_dictionary[invoked] = {} 			# Key 'invoked' not in the stats dictionary --> create it (empty)
						stats_dictionary[invoked][invoker] = 1 	# Create key 'invoker' in the 'invoked' dictionary and set it 1

		# In case that it is time to create the stats file, add t1 to time_start and write the dictionary in the stats_agent_XX.json
		if current_time-time_start >= t1:
			time_start += t1
			loader.write_dictionary(stats_dictionary, stats_file_path)
			stats_dictionary = {}

		# Wait 1 second to look for more data in the queue
		time.sleep(1)


# This function passes the initial data to the FlaskProcess through the mp_queue, tells it to launch the FlaskThread and checks
# if it has worked correctly with no port collisions. If everything is ok, retrives the used local_port. If there is a problem
# (a port collision), restarts the FlaskProcess.
def init_flask_process_and_check_ok(cold_redeploy):
	global my_agent_ID, my_project_folder, fs_path, start_port_search, mp_flask2agent_queue, mp_agent2flask_queue, flask_proc
	global array_var_ip, value_var_port, value_var_grant
	# Create the init_info_item for FlaskProcess
	# {"init_info": {"my_agent_ID": my_agent_ID, "my_project_folder": my_project_folder, "fs_path": fs_path, 
	#				"start_port_search": start_port_search}}
	init_info_item = {}
	init_info_item["init_info"] = {}
	init_info_item["init_info"]["my_agent_ID"] = my_agent_ID
	init_info_item["init_info"]["my_project_folder"] = my_project_folder
	init_info_item["init_info"]["fs_path"] = fs_path
	init_info_item["init_info"]["start_port_search"] = start_port_search
	init_info_item["init_info"]["verbose"] = verbose

	# Create the launch_item for the FlaskProcess
	# {"launch_info": True}
	launch_item = {}
	launch_item["launch_info"] = {}
	launch_item["launch_info"]["cold_redeploy"] = cold_redeploy

	# If cold_redeploy, create virtual restart request from the flask proecess
	if cold_redeploy:
		mp_queue_data = {}
		mp_queue_data["restart_flask_proc"] = "Requested restart from deployer (cold redeploy)."
		mp_flask2agent_queue.put(mp_queue_data)
	# Else, pass the items to FlaskProcess through the agent2flask queue
	else:
		mp_agent2flask_queue.put(init_info_item)
		mp_agent2flask_queue.put(launch_item)

	# Check the FlaskProcess launched the FlaskThread correctly and there are no collisions on ports (and retrieve local_port).
	# If there is a port collision, restart the FlaskProcess
	flask_proc_ok = False
	while not flask_proc_ok:
		while not mp_flask2agent_queue.empty():
			item = mp_flask2agent_queue.get()

			if "flask_proc_ok" in item:
				try:
					local_port = item["flask_proc_ok"]["local_port"]
					flask_proc_ok = True
					break
				except Exception as e:
					print(ERR_QUEUE_KEY_VALUE)
					raise e

			elif "restart_flask_proc" in item:
				# try:
				# 	restart_reason = item["restart_flask_proc"]
				# 	print(restart_reason)
				# except Exception as e:
				# 	print(ERR_QUEUE_KEY_VALUE)
				# 	raise e
				try:
					print("Restarting the flask process...")
					# Create new mp_queues (so that they are clear)
					mp_agent2flask_queue = Queue()
					mp_flask2agent_queue = Queue()

					# Terminate and create a new FlaskProcess
					flask_proc.terminate()
					proc_args = (mp_agent2flask_queue, mp_flask2agent_queue, mp_stats_queue,\
								 stdin_stream, value_var_grant, array_var_ip, value_var_port)
					flask_proc = Process(target=flaskProcessFunction, args=proc_args)
					flask_proc.start()

					# Pass initial info and launch
					mp_agent2flask_queue.put(init_info_item)
					mp_agent2flask_queue.put(launch_item)
					break

				except Exception as e:
					print(GEN_ERR_RESTARTING_FLASK)
					raise e

			else:
				print(ERR_QUEUE_KEY_VALUE)

		time.sleep(1)

	if local_port:
		# Next time the function is called, it will try to start in the same port as before
		start_port_search = local_port
		return local_port
	else:
		raise Exception(GEN_ERR_INIT_CHECK_FLASK)


# This function finds the first port available strating from the port given as parameter onwards. Returns the port and the
# socket which is blocking the port for other applications (close it before attempting to run any application in that port).
def get_port_available(port):
	available = False
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	while not available:
		try:
			sock.bind(("0.0.0.0", port))
			print("Port " + str(port) + " is available.")
			available = True
		except:
			print("Port " + str(port) + " is in use.")
			sock.close()
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			port += 1
	return (port, sock)


# This function gets the local IP. In the case of multiple IPs, gets the default route.
def get_local_ip():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		# doesn't even have to be reachable
		s.connect(('10.255.255.255', 1))
		local_ip = s.getsockname()[0]
	except:
		local_ip = '127.0.0.1'
	finally:
		s.close()
	return local_ip


# This function gets the local IP if the lan_mode is set to True and the external IP and port if the lan_mode is set to False.
# The function raises an exception if it could not retrieve the requested data.
def get_port_and_ip(lan_mode=True):
	ip, port = None, None

	if lan_mode:
		ip = get_local_ip()
		if ip==None:
			raise Exception(ERR_NO_LAN)
	else:
		(_, ip, port) = get_ip_info() 
		if ip==None or port==None:
			raise Exception(ERR_NO_INTERNET)
	return (ip, port)


# This function checks if cloudbook is already running in order not to load critical DUs in cold redeploy.
# If force_remove is specified to be True, RUNNING file is removed (True will be returned if removed).
def cloudbook_is_running(force_remove=False):
	running_file_path = fs_path + os.sep + "RUNNING"
	running = False
	if os.path.exists(running_file_path):
		print("RUNNING file found.")
		running = True
		if force_remove:
			removed = False
			while not removed:
				try:
					os.remove(running_file_path)
				except Exception as e:
					print("Cloud not remove RUNNING file. Retrying...")
					time.sleep(0.1)
			print("RUNNING file was successfully removed.")
	return running


# This function checks if there are any redeployment files
def check_redeploy_files():
	hot_redeploy_file_path = fs_path + os.sep + "HOT_REDEPLOY"
	cold_redeploy_file_path = fs_path + os.sep + "COLD_REDEPLOY"
	hot_redeploy = False
	cold_redeploy = False
	if os.path.exists(hot_redeploy_file_path):
		print("HOT_REDEPLOY file found.")
		hot_redeploy = True
	if os.path.exists(cold_redeploy_file_path):
		print("COLD_REDEPLOY file found.")
		cold_redeploy = True
	return (hot_redeploy, cold_redeploy)


# This function check if a du is critical
def is_critical(du):
	critical_dus_file_path = fs_path + os.sep + "critical_dus.json"
	critical_dus_dict = loader.load_dictionary(critical_dus_file_path)
	critical_dus = critical_dus_dict["critical_dus"]
	return du in critical_dus



#####   AGENT MAIN   #####
if __name__ == "__main__":

	# Set Ctrl+C handler
	signal.signal(signal.SIGINT, sigint_handler)

	# Save input stream to be able to use input in console of agent_0 for interactive programs
	stdin_stream = sys.stdin.fileno()

	# Program name is not parameter
	args = sys.argv[:]
	args.pop(0)
	#print("Arguments:", args, "\n")

	# Check if user asks for help
	if any(i in args for i in ["-help", "-syntax", "-info"]):
		print(COMMAND_SYNTAX)
		os._exit(0)
    
	# Assert existence of mandatory parameters
	if "-agent_id" not in args:
		print("The '-agent_id' parameter is mandatory. Note: must be followed by the <agent_id>.")
		print("For more info type 'agent.py -help'")
		os._exit(1)
	if "-project_folder" not in args:
		print("The '-project_folder' parameter is mandatory. Note: must be followed by the <project_folder>.")
		print("For more info type 'agent.py -help'")
		os._exit(1)

	# Analyze parameters
	agent_file = None
	skip = False
	try:
		for i in range(len(args)):
			if skip:
				skip = False
				continue
			if args[i]=="-agent_id":
				agent_file = args[i+1]
				skip = True
				continue
			if args[i]=="-project_folder":
				my_project_folder = args[i+1]
				skip = True
				continue
			if args[i]=="-verbose":
				verbose = True
				continue
			# if args[i]=="-log":
			# 	log_to_file = True
			# 	continue
	except Exception as e:
		print("The syntax is not correct. Use:")
		print("  agent.py -agent_id <agent_id> -project_folder <project_folder> [-verbose] [-help|-syntax|-info]")
		print("For more info type 'agent.py -help'")
		os._exit(1)

	if verbose:
		print("Parameters detected:")
		print("agent_id:", agent_file)
		print("project_folder:", my_project_folder)
		print("verbose:", verbose)
		# print("log:", log_to_file)

	##MIRO SI LA OPCION ES CREAR AGENTE
	if any(i in args for i in ["create"]):
		create_agent(grant=2, project_name=my_project_folder, fs="", agent_0=agent_file)
		print("Agent Created!")
		os._exit(1)


	# Create multiprocessing Values and Arrays
	value_var_grant = Value("i", 0) 		# Value (integer with initial value 0) sharable by processes
	array_var_ip = Array('c', range(15))	# Array (characters) sharable by processes. IP length is at most 4 3-digit numbers and 3 dots
	string2array("", array_var_ip)
	value_var_port = Value("i", 0) 			# Value (integer with initial value 0) sharable by processes

	# Load agent config file
	project_path = cloudbook_path + os.sep + my_project_folder
	agent_config_dict = loader.load_dictionary(project_path + os.sep + "agents" + os.sep + "config_"+agent_file+".json")

	my_agent_ID = agent_config_dict["AGENT_ID"]
	fs_path = agent_config_dict["DISTRIBUTED_FS"]
	num2value(grant2num(agent_config_dict["GRANT_LEVEL"]), value_var_grant)

	# If agent is the agent_0, clear the RUNNING file (a previous execution did not end correctly with return)
	if my_agent_ID=="agent_0":
		cloudbook_is_running(force_remove=True)

	# Change working directory
	os.chdir(fs_path + os.sep + "working_dir")

	# Load circle config file
	configjson_dict = loader.load_dictionary(fs_path + os.sep + "config.json")

	agent_stats_interval = configjson_dict['AGENT_STATS_INTERVAL']
	agent_grant_interval = configjson_dict['AGENT_GRANT_INTERVAL']
	lan_mode = configjson_dict['LAN']

	# Check if fs_path is not empty
	if fs_path=='':
		fs_path = poject_path + os.sep + "distributed"
		print("Path to distributed filesystem was not set in the agent, default will be used: ", fs_path)

	# Print settings
	settings_string = "\n"
	settings_string += "The agent has the following configuration:\n"
	settings_string += "  - ID: " + my_agent_ID + "\n"
	settings_string += "  - Project: " + my_project_folder + "\n"
	settings_string += "  - Grant: " + num2grant(value2num(value_var_grant)) + "\n"
	settings_string += "  - FSPath: " + fs_path + "\n"
	settings_string += "  - Stats creation period: " + str(agent_stats_interval) + "\n"
	settings_string += "  - Grant file creation period: " + str(agent_grant_interval) + "\n"
	if lan_mode:
		settings_string += "  - Lan mode: ON (using local ip and port)\n"
	else:
		settings_string += "  - Lan mode: OFF (using external ip and port)\n"
	print(settings_string)

	# Input/output queues for process communication
	mp_agent2flask_queue = Queue()
	mp_flask2agent_queue = Queue()
	mp_stats_queue = Queue()

	# Launch the FlaskProcess
	proc_args = (mp_agent2flask_queue, mp_flask2agent_queue, mp_stats_queue,\
				 stdin_stream, value_var_grant, array_var_ip, value_var_port)
	flask_proc = Process(target=flaskProcessFunction, args=proc_args)
	flask_proc.start()

	# Launch the stats file creator thread
	threading.Thread(target=create_stats, args=(agent_stats_interval,)).start()

	# Try (up to 3 times) to get ip and port to share with the rest of cloudbook
	retrys = 3
	for i in range(retrys):
		try:
			(ip, port) = get_port_and_ip(lan_mode=lan_mode)
			break
		except Exception as e:
			print(e)
			if i!=retrys:
				time.sleep(1)
				print("Retrying...")
			else:
				raise e

	# Number where the search for a free port will begin
	start_port_search = 5000

	# Does not need arguments because this is the global name space, and all these variables can be accessed as globals
	local_port = init_flask_process_and_check_ok(cold_redeploy=False)

	# Update the port (from None to the local_port) in the case of a lan_mode is active
	if lan_mode:
		port = local_port

	string2array(ip, array_var_ip)
	num2value(port, value_var_port)

	# Create and fill dictionary with initial data
	grant_dictionary = {}
	grant_dictionary[my_agent_ID] = {}
	grant_dictionary[my_agent_ID]["GRANT"] = num2grant(value2num(value_var_grant))
	grant_dictionary[my_agent_ID]["IP"] = ip
	grant_dictionary[my_agent_ID]["PORT"] = port

	# Build the paths to the different files
	agent_X_grant_file_path = project_path + os.sep + "distributed" + os.sep + "agents_grant" + os.sep + my_agent_ID+"_grant.json"
	agents_grant_file_path = project_path + os.sep + "distributed" + os.sep + "agents_grant.json"
	cloudbookjson_file_path = fs_path + os.sep + "cloudbook.json"

	# Internal function to write the "agent_X_grant.json" file consumed by the deployer
	def write_agent_X_grant_file():
		#print("Grant file will be updated with: ", grant_dictionary)
		loader.write_dictionary(grant_dictionary, agent_X_grant_file_path)

	# Internal function to load the "agents_grant.json" file created by the deployer
	def read_agents_grant_file():
		global agents_grant
		agents_grant = loader.load_dictionary(agents_grant_file_path)
		#print("agents_grant.json has been read.\n agents_grant = ", agents_grant)

	# Internal function to load the "cloudbook.json" file created by the deployer
	def read_cloudbook_file():
		global cloudbook_dict_agents
		global du_list
		cloudbook_dict_agents = loader.load_dictionary(cloudbookjson_file_path)
		#print("cloudbook.json has been read.\n cloudbook_dict_agents = ", cloudbook_dict_agents)
		du_list = loader.load_cloudbook_agent_dus(my_agent_ID, cloudbook_dict_agents)

	# Get the cloudbook and the agents_grant (DUs and IP/port of each agent).
	while not du_list:
		try:
			write_agent_X_grant_file()
			while not os.path.exists(agents_grant_file_path) or not os.path.exists(cloudbookjson_file_path) or os.stat(cloudbookjson_file_path).st_size==0:
				print("Waiting for agents_grant.json and cloudbook.json")
				if not os.path.exists(agent_X_grant_file_path):
					print("My grant file was deleted! Creating it again...")
					write_agent_X_grant_file()
				time.sleep(1)
			read_agents_grant_file()
			read_cloudbook_file()
		except:
			print(ERR_READ_WRITE)
			time.sleep(1)
			print("Retrying...")

	print("My du_list: ", du_list)

	# Pass the deploy_info to the FlaskProcess
	# {"deploy_info": {"du_list": du_list, "cloudbook_dict_agents": cloudbook_dict_agents, "agents_grant": agents_grant}}
	deploy_info_item = {}
	deploy_info_item["deploy_info"] = {}
	deploy_info_item["deploy_info"]["new_du_list"] = du_list
	deploy_info_item["deploy_info"]["cloudbook_dict_agents"] = cloudbook_dict_agents
	deploy_info_item["deploy_info"]["agents_grant"] = agents_grant
	mp_agent2flask_queue.put(deploy_info_item)

	# Forever loop (check grant modifications, write grant_XX_file, check and handle redeploy requests)
	time_start = time.monotonic()
	while True:
		# Load agent config file and update grant. Note: fspath changes are not taken into account while executing
		dict_for_grant_check = loader.load_dictionary(project_path + os.sep + "agents" + os.sep + "config_"+my_agent_ID+".json")
		grant_in_file = dict_for_grant_check["GRANT_LEVEL"]

		if grant_in_file!=num2grant(value2num(value_var_grant)):
			num2value(grant2num(grant_in_file), value_var_grant)
			grant_dictionary[my_agent_ID]["GRANT"] = num2grant(value2num(value_var_grant))
			print("New grant has been configured:", num2grant(value2num(value_var_grant)))

		# When the the interval time expires
		if time.monotonic()-time_start >= agent_grant_interval:
			time_start += agent_grant_interval

			# Check if there are redeployment files
			(hot_redeploy, cold_redeploy) = check_redeploy_files()
			if hot_redeploy:
				print("Executing HOT_REDEPLOY...")
				read_agents_grant_file()
				read_cloudbook_file()
				# Pass the init_info to the FlaskProcess
				# {"deploy_info": {"cloudbook_dict_agents": cloudbook_dict_agents, "agents_grant": agents_grant}}
				deploy_info_item = {}
				deploy_info_item["deploy_info"] = {}
				deploy_info_item["deploy_info"]["cloudbook_dict_agents"] = cloudbook_dict_agents
				deploy_info_item["deploy_info"]["agents_grant"] = agents_grant
				deploy_info_item["deploy_info"]["new_du_list"] = du_list
				mp_agent2flask_queue.put(deploy_info_item)
				
			if cold_redeploy:
				print("Executing COLD_REDEPLOY...")
				flask_proc.terminate()
				local_port = init_flask_process_and_check_ok(cold_redeploy=True)

				# Update the port (from None to the local_port) in the case of a lan_mode is active
				if lan_mode:
					port = local_port
				grant_dictionary[my_agent_ID]["PORT"] = port

				# It is supposed that agents_grant.json and cloudbook.json already exists
				read_agents_grant_file()
				read_cloudbook_file()

				print("My new du_list: ", du_list)

				# Pass the deploy_info to the FlaskProcess
				# {"deploy_info": {"new_du_list": du_list, "cloudbook_dict_agents": cloudbook_dict_agents, "agents_grant": agents_grant}}
				deploy_info_item = {}
				deploy_info_item["deploy_info"] = {}
				deploy_info_item["deploy_info"]["new_du_list"] = du_list
				deploy_info_item["deploy_info"]["cloudbook_dict_agents"] = cloudbook_dict_agents
				deploy_info_item["deploy_info"]["agents_grant"] = agents_grant
				mp_agent2flask_queue.put(deploy_info_item)

			# Update also IP/port ??? --> call get_ip_info() again and update if necessary
			#grant_dictionary[my_agent_ID]["IP"] = ip
			#grant_dictionary[my_agent_ID]["PORT"] = port

			# Write dictionary in "agent_X_grant.json" to communicate changes and prove agent is alive
			write_agent_X_grant_file()

		# Wait 1 second before next iteration in the loop
		time.sleep(1)

	print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
