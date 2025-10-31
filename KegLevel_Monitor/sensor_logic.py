_G='calculated_starting_volume_liters'
_F='update_cal_data_cb'
_E='Nominal'
_D=None
_C=True
_B=False
_A=.0
import time,threading,math
' GPIO PINOUT FOR REFERENCE\nLabel ------------ Pin - Pin ------------ Label\n3V3 power---------  1     2  ------------ 5V power\nGPIO 2 (SDA) -----  3     4  ------------ 5V power\nGPIO 3 (SCL) -----  5     6  ------------ Ground\nGPIO 4 (GPCLK0) --  7     8  ------------ GPIO 14 (TXD)\nGround -----------  9    10  ------------ GPIO 15 (RXD)\nGPIO 17 ---------- 11    12  ------------ GPIO 18 (PCM_CLK)\nGPIO 27 ---------- 13    14  ------------ Ground\nGPIO 22 ---------- 15    16  ------------ GPIO 23\n3V3 power -------- 17    18  ------------ GPIO 24\nGPIO 10 (MOSI) --- 19    20  ------------ Ground\nGPIO 9 (MISO) ---- 21    22  ------------ GPIO 25\nGPIO 11 (SCLK) --- 23    24  ------------ GPIO 8 (CE0)\nGround ----------- 25    26  ------------ GPIO 7 (CE1)\nGPIO 0 (ID_SD) --- 27    28  ------------ GPIO 1 (ID_SC)\nGPIO 5 ----------- 29    30  ------------ Ground\nGPIO 6 ----------- 31    32  ------------ GPIO 12 (PWM0)\nGPIO 13 (PWM1) --- 33    34  ------------ Ground\nGPIO 19 (PCM_FS) - 35    36  ------------ GPIO 16\nGPIO 26 ---------- 37    38  ------------ GPIO 20 (PCM_DIN)\nGround ----------- 39    40  ------------ GPIO 21 (PCM_DOUT)\n'
try:
	import RPi.GPIO as GPIO
	if GPIO.getmode()!=GPIO.BCM:GPIO.setmode(GPIO.BCM)
	print('Running on RPi hardware (RPi.GPIO mode).');IS_RASPBERRY_PI_MODE=_C
except ImportError:
	class MockGPIO:
		def setmode(A,mode):0
		def setup(A,pin,direction,pull_up_down=_D):0
		def output(A,pin,state):0
		def input(A,pin):return 0
		def setwarnings(A,state):0
		def cleanup(A,pin=_D):0
		def add_event_detect(A,pin,edge,callback,bouncetime):0
		def remove_event_detect(A,pin):0
	GPIO=MockGPIO();print('Running in Mock Mode (RPi.GPIO not available).');IS_RASPBERRY_PI_MODE=_B
FLOW_SENSOR_PINS=[5,6,12,13,16,25,26,7,20,21]
READING_INTERVAL_SECONDS=.5
FLOW_DEBOUNCE_MS=5
FLOW_PULSES_FOR_ACTIVITY=10
FLOW_PULSES_FOR_STOPPED=3
DEFAULT_K_FACTOR=588e1
GPIO_LIB=GPIO
HARDWARE_AVAILABLE=IS_RASPBERRY_PI_MODE
global_pulse_counts=[0]*len(FLOW_SENSOR_PINS)
last_check_time=[_A]*len(FLOW_SENSOR_PINS)
def count_pulse(channel):
	'Interrupt handler: Increments the pulse count for the active channel.'
	try:A=FLOW_SENSOR_PINS.index(channel);global_pulse_counts[A]+=1
	except ValueError:pass
class SensorLogic:
	def __init__(A,num_sensors_from_config,ui_callbacks,settings_manager,notification_service):
		B=num_sensors_from_config;A.num_sensors=B;A.ui_callbacks=ui_callbacks;A.settings_manager=settings_manager;A.notification_service=notification_service
		if A.num_sensors>len(FLOW_SENSOR_PINS):A.num_sensors=len(FLOW_SENSOR_PINS);print(f"Warning: Number of sensors requested ({B}) is more than available pins. Using {A.num_sensors} sensors.")
		A.sensor_pins=FLOW_SENSOR_PINS[:A.num_sensors];A.keg_ids_assigned=[_D]*A.num_sensors;A.keg_dispensed_liters=[_A]*A.num_sensors;A.current_flow_rate_lpm=[_A]*A.num_sensors;A.tap_is_active=[_B]*A.num_sensors;A.active_sensor_index=-1;A.last_pulse_count=[0]*A.num_sensors;A._is_calibrating=_B;A._cal_target_tap=-1;A._cal_start_pulse_count=0;A._cal_current_session_liters=_A;A._cal_target_volume_user_unit=_A;A.raw_readings_buffer=[[]for A in range(A.num_sensors)];A.loop_count=0;A._running=_B;A.is_paused=_B;A.last_known_remaining_liters=[_D]*A.num_sensors;A.sensor_thread=_D;A._load_initial_volumes()
	def start_flow_calibration(A,tap_index,target_volume_user_unit_str):
		B=tap_index;global global_pulse_counts
		if A._running and 0<=B<A.num_sensors:
			try:C=float(target_volume_user_unit_str)
			except ValueError:print('SensorLogic Cal Error: Invalid target volume.');return _B
			A._is_calibrating=_C;A._cal_target_tap=B;A._cal_target_volume_user_unit=C;A._cal_start_pulse_count=global_pulse_counts[B];A._cal_current_session_liters=_A;A.active_sensor_index=B;A.tap_is_active[B]=_C;print(f"SensorLogic Cal: Started for tap {B+1} at pulse {A._cal_start_pulse_count}");return _C
		return _B
	def stop_flow_calibration(A,tap_index):
		B=tap_index;global global_pulse_counts
		if not A._is_calibrating or A._cal_target_tap!=B:return 0,_A
		E=time.time();F=E-last_check_time[B];G=A.settings_manager.get_flow_calibration_factors();H=G[B];I=global_pulse_counts[B]-A.last_pulse_count[B];J,K=A._calculate_calibration_metrics(B,I,F,H);C=global_pulse_counts[B]-A._cal_start_pulse_count;D=A._cal_current_session_liters;A.ui_callbacks.get(_F)(_A,D);A._is_calibrating=_B;A._cal_target_tap=-1;A.active_sensor_index=-1;A.tap_is_active[B]=_B;print(f"SensorLogic Cal: Stopped for tap {B+1}. Total Pulses: {C}");return C,D
	def _calculate_calibration_metrics(A,tap_index,pulses,time_interval,k_factor):
		'Calculates flow metrics only for the calibration session, without impacting main keg levels.';F=time_interval;E=pulses;B=k_factor
		if B==0 or F==0:C=_A;D=_A
		else:C=E/B/(F/6e1);D=E/B
		A._cal_current_session_liters+=D
		if A._is_calibrating and A._cal_target_tap==tap_index and A.ui_callbacks.get(_F):A.ui_callbacks.get(_F)(C,A._cal_current_session_liters)
		return C,D
	def _load_initial_volumes(A):
		'Loads the dispensed volume and total starting volume from the Keg Library.';F=A.settings_manager.get_sensor_keg_assignments()
		for B in range(A.num_sensors):
			D=F[B];C=A.settings_manager.get_keg_by_id(D);A.keg_ids_assigned[B]=D
			if C:E=C.get('current_dispensed_liters',_A);G=C.get(_G,_A);A.keg_dispensed_liters[B]=E;H=max(_A,G-E);A.last_known_remaining_liters[B]=H
			else:A.keg_dispensed_liters[B]=_A;A.last_known_remaining_liters[B]=_A
	def start_monitoring(A):
		if not HARDWARE_AVAILABLE:
			for B in range(A.num_sensors):A._update_ui_data(B,_A,A.last_known_remaining_liters[B],_E)
			return
		A._setup_gpios();A._running=_C;A.is_paused=_B
		if A.sensor_thread is _D or not A.sensor_thread.is_alive():A.sensor_thread=threading.Thread(target=A._sensor_loop,daemon=_C);A.sensor_thread.start()
	def stop_monitoring(A):
		A._running=_B
		if A.sensor_thread and A.sensor_thread.is_alive():A.sensor_thread.join(timeout=READING_INTERVAL_SECONDS+2)
		A._release_gpio_resources();print('SensorLogic: Monitoring stopped and resources released.')
	def _release_gpio_resources(A):
		print('SensorLogic: Releasing GPIO resources...')
		if HARDWARE_AVAILABLE:
			try:
				try:
					for B in A.sensor_pins:
						try:GPIO_LIB.remove_event_detect(B)
						except Exception:pass
				except Exception:pass
				GPIO_LIB.cleanup();print('SensorLogic: GPIO resources cleaned up.')
			except Exception as C:print(f"SensorLogic Warning: GPIO cleanup failed: {C}")
	def _setup_gpios(B):
		if not HARDWARE_AVAILABLE:return
		print('SensorLogic: Setting up GPIO pins for flow meters...');GPIO_LIB.setmode(GPIO_LIB.BCM)
		for A in B.sensor_pins:GPIO_LIB.setup(A,GPIO_LIB.IN,pull_up_down=GPIO_LIB.PUD_DOWN);GPIO_LIB.add_event_detect(A,GPIO_LIB.RISING,callback=count_pulse,bouncetime=FLOW_DEBOUNCE_MS)
		print('SensorLogic: GPIO setup complete.')
	def pause_acquisition(A):A.is_paused=_C;print('SensorLogic: Monitoring paused.')
	def resume_acquisition(A):A.is_paused=_B;A._load_initial_volumes();print('SensorLogic: Resuming. Initial volumes reloaded.')
	def force_recalculation(A):'Forces the logic to reload all initial volumes.';print('SensorLogic: Forcing recalculation/reload of initial volumes.');A._load_initial_volumes()
	def _update_ui_data(A,sensor_index,flow_rate_lpm,remaining_liters,status_string):
		"Helper to send updates to the UI's queue.";E='update_sensor_stability_cb';D='update_sensor_data_cb';C=status_string;B=sensor_index
		if A.ui_callbacks.get(D):A.ui_callbacks.get(D)(B,flow_rate_lpm,remaining_liters,C)
		if A.ui_callbacks.get(E):A.ui_callbacks.get(E)(B,'Data stable'if C==_E else'Acquiring data...')
	def _sensor_loop(A):
		global global_pulse_counts;global last_check_time
		if all(A==_A for A in last_check_time):
			E=time.time()
			for B in range(len(FLOW_SENSOR_PINS)):last_check_time[B]=E
		while A._running:
			if A.is_paused:time.sleep(.5);continue
			if A._is_calibrating and A._cal_target_tap!=-1:A.active_sensor_index=A._cal_target_tap;A.tap_is_active[A._cal_target_tap]=_C
			E=time.time();J=A.settings_manager.get_displayed_taps();K=A.settings_manager.get_flow_calibration_factors();G=-1
			if not A._is_calibrating and A.active_sensor_index==-1:
				for B in range(J):
					D=E-last_check_time[B];C=global_pulse_counts[B]-A.last_pulse_count[B]
					if C>=FLOW_PULSES_FOR_ACTIVITY and D>0:G=B;break
			elif not A._is_calibrating and A.active_sensor_index!=-1:G=A.active_sensor_index
			if A._is_calibrating:A.active_sensor_index=A._cal_target_tap
			else:A.active_sensor_index=G
			for B in range(J):
				D=E-last_check_time[B];C=global_pulse_counts[B]-A.last_pulse_count[B];H=B==A.active_sensor_index;I=A._is_calibrating and A._cal_target_tap==B
				if H and D>0 and C>0:
					F=K[B]
					if I:A._calculate_calibration_metrics(B,C,D,F);A.tap_is_active[B]=_C
					else:A._process_flow_data(B,C,D,F);A.tap_is_active[B]=_C
				elif A.tap_is_active[B]and not H:A.tap_is_active[B]=_B;A._update_ui_data(B,_A,A.last_known_remaining_liters[B],_E)
				elif A.tap_is_active[B]and H and C<=FLOW_PULSES_FOR_STOPPED:
					F=K[B]
					if I:A._calculate_calibration_metrics(B,C,D,F)
					else:A._process_flow_data(B,C,D,F)
					A.tap_is_active[B]=_B;A.active_sensor_index=-1;A._update_ui_data(B,_A,A.last_known_remaining_liters[B],_E);print(f"SensorLogic: Tap {B+1} stopped. Lock released.")
					if not I:A.settings_manager.save_all_keg_dispensed_volumes()
				elif not A.tap_is_active[B]:A._update_ui_data(B,_A,A.last_known_remaining_liters[B],_E);A._check_conditional_notification(B)
				A.last_pulse_count[B]=global_pulse_counts[B];last_check_time[B]=E
			A.notification_service.check_and_send_temp_notification();time.sleep(READING_INTERVAL_SECONDS)
		print('SensorLogic: Sensor loop ended.')
	def _calculate_flow_metrics(A,sensor_index,pulses,time_interval,k_factor):
		'Helper to calculate flow rate, dispensed volume, and remaining volume, and persist the dispensed volume.';I=time_interval;H=pulses;D=k_factor;B=sensor_index
		if D==0 or I==0:E=_A;F=_A
		else:E=H/D/(I/6e1);F=H/D
		A.keg_dispensed_liters[B]+=F;G=A.keg_ids_assigned[B]
		if G:A.settings_manager.update_keg_dispensed_volume(G,A.keg_dispensed_liters[B])
		J=A.settings_manager.get_keg_by_id(G);K=J.get(_G,_A)if J else _A;C=K-A.keg_dispensed_liters[B];C=max(_A,C);A.last_known_remaining_liters[B]=C;A._update_ui_data(B,E,C,_E);return E,F,C
	def _process_flow_data(A,sensor_index,pulses,time_interval,k_factor):'Calculates flow rate, dispensed volume, and remaining volume, and persists the dispensed volume.';B=sensor_index;C,D,E=A._calculate_flow_metrics(B,pulses,time_interval,k_factor);A._check_conditional_notification(B,force_check=_C)
	def _check_conditional_notification(B,sensor_index,force_check=_B):
		'Checks if the remaining volume is below the threshold and triggers notification.';G='None';A=sensor_index;C=B.last_known_remaining_liters[A]
		if C is _D:return
		D=B.settings_manager.get_conditional_notification_settings();H=D.get('notification_type',G);E=D.get('threshold_liters',4.);F=D.get('sent_notifications',[])
		if H!=G:
			if C<=E and not F[A]and force_check:B.notification_service.send_conditional_notification(A,C,E)
			I=E*1.25
			if F[A]and C>I:B.settings_manager.update_conditional_sent_status(A,_B)