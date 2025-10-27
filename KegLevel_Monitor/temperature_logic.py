_Q='No Sensor'
_P='unassigned'
_O='temp_f'
_N='update_temp_display_cb'
_M='timestamp'
_L='monthly_log'
_K='weekly_log'
_J='daily_log'
_I='month'
_H='week'
_G='day'
_F='avg'
_E='low'
_D='high'
_C='high_low_avg'
_B='last_updated'
_A=None
import time,threading,json,os,glob
from datetime import datetime,timedelta
class TemperatureLogic:
	def __init__(A,ui_callbacks,settings_manager):A.ui_callbacks=ui_callbacks;A.settings_manager=settings_manager;A.ambient_sensor=_A;A._temp_thread=_A;A._running=False;A._stop_event=threading.Event();A.last_known_temp_f=_A;A.last_update_time=_A;B=A.settings_manager.get_base_dir();A.log_file=os.path.join(B,'temperature_log.json');A.log_data={_J:[],_K:[],_L:[],_C:{_G:{_D:_A,_E:_A,_F:_A,_B:_A},_H:{_D:_A,_E:_A,_F:_A,_B:_A},_I:{_D:_A,_E:_A,_F:_A,_B:_A}}};A._load_log_data()
	def reset_log(A):'Clears all in-memory log data and saves the reset log to file.';A.log_data={_J:[],_K:[],_L:[],_C:{_G:{_D:_A,_E:_A,_F:_A,_B:_A},_H:{_D:_A,_E:_A,_F:_A,_B:_A},_I:{_D:_A,_E:_A,_F:_A,_B:_A}}};A._save_log_data();print('TemperatureLogic: Temperature log has been reset.')
	def _find_sensor(A):0
	def get_assigned_sensor(A):
		'Gets the assigned ambient sensor ID based on settings.';A.ambient_sensor=A.settings_manager.get_system_settings().get('ds18b20_ambient_sensor',_A)
		if not A.ambient_sensor or A.ambient_sensor==_P:print('TemperatureLogic: No ambient sensor assigned or found.')
	def detect_ds18b20_sensors(C):'Finds all available DS18B20 sensors and returns their IDs by reading the filesystem.';A='/sys/bus/w1/devices/';B=glob.glob(A+'28-*');return[os.path.basename(A)for A in B]
	def _read_temp_from_id(K,sensor_id):
		'Reads the temperature from a sensor given its ID.';A=sensor_id
		if not A or A==_P:return
		F=f"/sys/bus/w1/devices/{A}/";C=F+'w1_slave'
		if not os.path.exists(C):print(f"TemperatureLogic: Sensor file not found for ID {A}.");return
		try:
			with open(C,'r')as D:B=D.readlines()
			while B[0].strip()[-3:]!='YES':
				time.sleep(.2)
				with open(C,'r')as D:B=D.readlines()
			E=B[1].find('t=')
			if E!=-1:G=B[1][E+2:];H=float(G)/1e3;I=H*9./5.+32.;return I
		except Exception as J:print(f"TemperatureLogic: Error reading temperature from sensor {A}: {J}");return
	def start_monitoring(A):
		if not A._running:
			A._running=True;A.get_assigned_sensor()
			if A.ambient_sensor:A._temp_thread=threading.Thread(target=A._monitor_loop,daemon=True);A._temp_thread.start();print('TemperatureLogic: Monitoring thread started.')
			else:print('TemperatureLogic: Cannot start monitoring, no ambient sensor assigned.');A.ui_callbacks.get(_N)(_A,_Q)
	def stop_monitoring(A):
		if A._running:
			A._running=False;A._stop_event.set()
			if A._temp_thread and A._temp_thread.is_alive():
				print('TemperatureLogic: Waiting for thread to stop...');A._temp_thread.join(timeout=2)
				if A._temp_thread.is_alive():print('TemperatureLogic: Thread did not stop gracefully.')
				else:print('TemperatureLogic: Thread stopped.')
	def _monitor_loop(A):
		while A._running:
			try:
				B=A.read_ambient_temperature()
				if B is not _A:
					A.last_known_temp_f=B;C=A.settings_manager.get_display_units()
					if C=='imperial':A.ui_callbacks.get(_N)(B,'F')
					else:D=(B-32)*(5/9);A.ui_callbacks.get(_N)(D,'C')
					A._log_temperature_reading(B)
				else:A.last_known_temp_f=_A;A.ui_callbacks.get(_N)(_A,_Q)
				A._stop_event.wait(300)
			except Exception as E:print(f"TemperatureLogic: Error in monitor loop: {E}");A.last_known_temp_f=_A;A.ui_callbacks.get(_N)(_A,'Error')
		print('TemperatureLogic: Monitor loop ended.')
	def _load_log_data(A):
		'Loads log data from the JSON file.'
		if os.path.exists(A.log_file):
			try:
				with open(A.log_file,'r')as C:
					A.log_data=json.load(C)
					for B in[_G,_H,_I]:
						if A.log_data[_C][B][_B]:A.log_data[_C][B][_B]=datetime.fromisoformat(A.log_data[_C][B][_B])
				print(f"TemperatureLogic: Log data loaded from {A.log_file}.")
			except(json.JSONDecodeError,KeyError,TypeError)as D:print(f"TemperatureLogic: Error loading log data from file: {D}. Starting with new log.")
	def _save_log_data(B):
		'Saves log data to the JSON file.'
		try:
			A=B.log_data.copy()
			for C in[_G,_H,_I]:
				if A[_C][C][_B]:A[_C][C][_B]=A[_C][C][_B].isoformat()
			with open(B.log_file,'w')as D:json.dump(A,D,indent=4)
			print(f"TemperatureLogic: Log data saved to {B.log_file}.")
		except Exception as E:print(f"TemperatureLogic: Error saving log data: {E}")
	def _log_temperature_reading(A,temp_f):'Adds a new temperature reading to the in-memory log and triggers a save.';B=temp_f;D=datetime.now();C=D.isoformat();A.log_data[_J].append({_M:C,_O:B});A.log_data[_K].append({_M:C,_O:B});A.log_data[_L].append({_M:C,_O:B});A._prune_logs(D);A._calculate_stats_and_update_log();A._save_log_data()
	def _prune_logs(A,now):'Removes old entries from the in-memory log data.';B=now;A.log_data[_J]=[A for A in A.log_data[_J]if datetime.fromisoformat(A[_M])>=B-timedelta(days=1)];A.log_data[_K]=[A for A in A.log_data[_K]if datetime.fromisoformat(A[_M])>=B-timedelta(weeks=1)];A.log_data[_L]=[A for A in A.log_data[_L]if datetime.fromisoformat(A[_M])>=B-timedelta(days=30)]
	def _calculate_stats(C,log_list):
		'Calculates high, low, and average from a list of readings.';B=log_list
		if not B:return _A,_A,_A
		A=[A[_O]for A in B];return max(A),min(A),sum(A)/len(A)
	def _calculate_stats_and_update_log(A):'Calculates and updates stats for day, week, and month.';B=datetime.now();C,D,E=A._calculate_stats(A.log_data[_J]);A.log_data[_C][_G]={_D:C,_E:D,_F:E,_B:B};F,G,H=A._calculate_stats(A.log_data[_K]);A.log_data[_C][_H]={_D:F,_E:G,_F:H,_B:B};I,J,K=A._calculate_stats(A.log_data[_L]);A.log_data[_C][_I]={_D:I,_E:J,_F:K,_B:B}
	def get_temperature_log(A):
		'Returns the current log data for display.';E=A.settings_manager.get_display_units();B={_G:A.log_data[_C][_G].copy(),_H:A.log_data[_C][_H].copy(),_I:A.log_data[_C][_I].copy()}
		if E=='metric':
			for C in[_G,_H,_I]:
				for D in[_D,_E,_F]:
					if B[C][D]is not _A:F=B[C][D];B[C][D]=(F-32)*(5/9)
		return B
	def read_ambient_temperature(A):
		'Reads the temperature from the assigned ambient sensor.'
		if A.ambient_sensor:B=A._read_temp_from_id(A.ambient_sensor);return B