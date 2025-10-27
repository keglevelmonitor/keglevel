_z='Monthly'
_y='Weekly'
_x='Hourly'
_w='imperial'
_v='BJCP 2021 Library'
_u='description'
_t='unassigned'
_s='full'
_r='source_library'
_q='ibu'
_p='lite'
_o='metric'
_n='licensing_api_url'
_m='Daily'
_l='starting_volume_liters'
_k='trial_lock_signature'
_j='None'
_i='current_dispensed_liters'
_h='name'
_g='high_temp_f'
_f='low_temp_f'
_e='threshold_liters'
_d='push_notification_settings'
_c='sensor_labels'
_b='license_key'
_a='ds18b20_ambient_sensor'
_Z=True
_Y='launch_workflow_on_start'
_X='autostart_enabled'
_W='display_units'
_V='frequency'
_U='displayed_taps'
_T='temp_sent_timestamps'
_S='notification_type'
_R='sent_notifications'
_Q='ui_mode'
_P='kegs'
_O='flow_calibration_notes'
_N='sensor_keg_assignments'
_M='sensor_beverage_assignments'
_L='smtp_port'
_K='flow_calibration_to_be_poured'
_J=None
_I='imperial_pour_oz'
_H='metric_pour_ml'
_G=False
_F='flow_calibration_factors'
_E='beverages'
_D='error_reported_times'
_C='id'
_B='conditional_notification_settings'
_A='system_settings'
import json,os,time,uuid,sys,hmac,hashlib
from datetime import datetime,timedelta
from pathlib import Path
SETTINGS_FILE='settings.json'
BEVERAGES_FILE='beverages_library.json'
PROCESS_FLOW_FILE='process_flow.json'
BJCP_2021_FILE='bjcp_2021_library.json'
KEG_LIBRARY_FILE='keg_library.json'
TRIAL_RECORD_FILE='trial_record.dat'
UNASSIGNED_KEG_ID='unassigned_keg_id'
try:from sensor_logic import FLOW_SENSOR_PINS,DEFAULT_K_FACTOR
except ImportError:FLOW_SENSOR_PINS=[17,18,19,20,21,22,23,24,25,26];DEFAULT_K_FACTOR=588e1
class SettingsManager:
	def _get_default_sensor_labels(A):return[f"Tap {A+1}"for A in range(A.num_sensors)]
	def _get_default_keg_definitions(E):
		D='starting_total_weight_kg';C='empty_weight_kg';B=[]
		for F in range(5):A={_C:str(uuid.uuid4()),'title':f"Keg {F+1:02}",C:4.5,D:23.5,_l:18.9,_i:.0};A[_l]=E._calculate_volume_from_weight(A[D],A[C]);B.append(A)
		return B
	def _get_default_sensor_keg_assignments(A):return[UNASSIGNED_KEG_ID]*A.num_sensors
	def _get_default_beverage_assignments(A):B=A._get_default_beverage_library().get(_E,[]);C=B[0][_C]if B else _J;return[C]*A.num_sensors
	def _get_default_push_notification_settings(A):return{_S:_j,_V:_m,'server_email':'','server_password':'','email_recipient':'','smtp_server':'',_L:'','sms_number':'','sms_carrier_gateway':''}
	def _get_default_conditional_notification_settings(A):return{_S:_j,_e:4.,_R:[_G]*A.num_sensors,_f:35.,_g:45.,_T:[],_D:{'push':0,'volume':0,'temperature':0}}
	def _get_default_system_settings(A):return{_W:_o,_U:5,_a:_t,_Q:_p,_b:'',_X:_G,_Y:_G,_F:[DEFAULT_K_FACTOR]*A.num_sensors,_H:355,_I:12,_O:'',_K:1e3,_n:'https://us-central1-keglevel-licensing-api.cloudfunctions.net/handle_licensing'}
	def _get_default_beverage_library(A):return{_E:[{_C:str(uuid.uuid4()),_h:'House Pale Ale','bjcp':'18(b)','abv':'5.0',_q:35,_u:'A refreshing, hop-forward American Pale Ale with a balanced malt background and a clean, dry finish. Our go-to beer.'}]}
	def _calculate_volume_from_weight(B,total_weight_kg,empty_weight_kg,density=1.):A=total_weight_kg-empty_weight_kg;return max(.0,A/density)
	def _calculate_weight_from_volume(B,volume_liters,empty_weight_kg,density=1.):A=volume_liters*density;return empty_weight_kg+A
	def __init__(A,num_sensors_expected):
		B=os.path.dirname(os.path.abspath(__file__));print(f"SettingsManager: Using script path: {B}");A.base_dir=B;A.settings_file_path=os.path.join(A.base_dir,SETTINGS_FILE);A.beverages_file_path=os.path.join(A.base_dir,BEVERAGES_FILE);A.process_flow_file_path=os.path.join(A.base_dir,PROCESS_FLOW_FILE);A.keg_library_file_path=os.path.join(A.base_dir,KEG_LIBRARY_FILE);A.trial_record_file_path=os.path.join(A.base_dir,TRIAL_RECORD_FILE);A.bjcp_2021_file_path=os.path.join(A.base_dir,BJCP_2021_FILE);A.num_sensors=num_sensors_expected;A.beverage_library=A._load_beverage_library();A.keg_library,A.keg_map=A._load_keg_library();A.settings=A._load_settings()
		if os.path.exists(A.trial_record_file_path):A.delete_obsolete_local_trial_files()
	def get_base_dir(A):return A.base_dir
	def _load_keg_library(C):
		B=C._get_default_keg_definitions()
		if os.path.exists(C.keg_library_file_path):
			try:
				with open(C.keg_library_file_path,'r')as D:
					A=json.load(D)
					if not isinstance(A.get(_P),list)or not A.get(_P):print(f"Keg Library: Contents corrupted or empty. Using default.");A={_P:B}
					E=A.get(_P,[]);F={A[_C]:A for A in E if _C in A};return A,F
			except Exception as G:print(f"Keg Library: Error loading or decoding JSON: {G}. Using default.");return{_P:B},{A[_C]:A for A in B}
		else:print(f"{KEG_LIBRARY_FILE} not found. Creating with defaults.");A={_P:B};C._save_keg_library(A);return A,{A[_C]:A for A in B}
	def _save_keg_library(A,library):
		try:
			with open(A.keg_library_file_path,'w')as B:json.dump(library,B,indent=4)
			print(f"Keg Library saved to {A.keg_library_file_path}.")
		except Exception as C:print(f"Error saving keg library: {C}")
	def get_keg_definitions(A):A.keg_library,A.keg_map=A._load_keg_library();return A.keg_library.get(_P,[])
	def save_keg_definitions(A,definitions_list):
		B=definitions_list
		if not B:B=A._get_default_keg_definitions()
		A.keg_library[_P]=B;A.keg_map={A[_C]:A for A in B};A._save_keg_library(A.keg_library);print('Keg definitions saved.')
	def delete_keg_definition(C,keg_id_to_delete):
		D=keg_id_to_delete;F=C.get_keg_definitions();E=[A for A in F if A.get(_C)!=D]
		if len(E)==len(F):print(f"SettingsManager Error: Keg ID {D} not found for deletion.");return _G,'Keg ID not found.'
		C.save_keg_definitions(E);A=C.get_sensor_keg_assignments();H=E[0][_C]if E else UNASSIGNED_KEG_ID;G=_G
		for B in range(len(A)):
			if A[B]==D:A[B]=H;G=_Z
		if G:
			for B in range(len(A)):C.save_sensor_keg_assignment(B,A[B])
			print(f"SettingsManager: Re-assigned taps after deleting Keg ID {D}.")
		return _Z,'Keg deleted and assignments updated.'
	def update_keg_dispensed_volume(A,keg_id,dispensed_liters):
		C=dispensed_liters;B=keg_id
		if B in A.keg_map:
			A.keg_map[B][_i]=C
			for D in A.keg_library[_P]:
				if D.get(_C)==B:D[_i]=C;break
			return _Z
		return _G
	def save_all_keg_dispensed_volumes(A):A._save_keg_library(A.keg_library)
	def get_keg_by_id(B,keg_id):
		A=keg_id
		if A==UNASSIGNED_KEG_ID:return{_C:UNASSIGNED_KEG_ID,'title':'Offline',_l:.0,_i:.0}
		return B.keg_map.get(A)
	def _load_beverage_library(A):
		if os.path.exists(A.beverages_file_path):
			try:
				with open(A.beverages_file_path,'r')as D:
					B=json.load(D)
					if not isinstance(B.get(_E),list):print(f"Beverage Library: Error loading library. Contents corrupted. Using default.");B={_E:A._get_default_beverage_library().get(_E,[])}
					return B
			except Exception as E:print(f"Beverage Library: Error loading or decoding JSON: {E}. Using default.");return{_E:A._get_default_beverage_library().get(_E,[])}
		else:print(f"{BEVERAGES_FILE} not found. Creating with defaults.");C=A._get_default_beverage_library();A._save_beverage_library(C);return C
	def _save_beverage_library(A,library):
		try:
			with open(A.beverages_file_path,'w')as B:json.dump(library,B,indent=4)
			print(f"Beverage Library saved to {A.beverages_file_path}.")
		except Exception as C:print(f"Error saving beverage library: {C}")
	def get_beverage_library(A):return A.beverage_library
	def save_beverage_library(A,new_library_list):A.beverage_library[_E]=new_library_list;A._save_beverage_library(A.beverage_library)
	def get_available_addon_libraries(D):
		G='_library.json';E=D.get_base_dir();C=[];F={os.path.basename(D.bjcp_2021_file_path):_v}
		try:
			for A in os.listdir(E):
				K=os.path.join(E,A);H=A.endswith(G);I=A==os.path.basename(BEVERAGES_FILE)
				if H and not I:
					if A in F:B=F[A]
					else:B=A.replace(G,'').replace('_',' ').strip();B=B.title()
					if B not in C:C.append(B)
			C.sort();return C
		except Exception as J:print(f"SettingsManager Error scanning for add-on libraries: {J}");return['Error Scanning']
	def get_addon_filename_from_display_name(A,display_name):
		B=display_name
		if B==_v:return A.bjcp_2021_file_path
		else:C=B.lower().replace(' ','_');return os.path.join(A.get_base_dir(),f"{C}_library.json")
	def load_addon_library(D,addon_name):
		A=addon_name;B=D.get_addon_filename_from_display_name(A)
		if os.path.exists(B):
			try:
				with open(B,'r',encoding='utf-8')as E:
					C=json.load(E)
					if not isinstance(C.get(_E),list):print(f"Addon Library: Contents of {A} corrupted. Aborting import.");return
					for F in C.get(_E,[]):F[_r]=A
					return C.get(_E,[])
			except Exception as G:print(f"Addon Library: Error loading or decoding JSON for {A}: {G}.");return
		else:print(f"Addon Library: {A} file not found at {B}.");return
	def import_beverages_from_addon(B,addon_name):
		A=addon_name;D=B.load_addon_library(A)
		if D is _J:return _G,f"Could not load {A} file.",0
		E=B.get_beverage_library().get(_E,[]);G={A[_C]for A in E if _C in A};C=[A for A in D if A.get(_C)not in G];F=len(C)
		if not C:return _G,f"{A} is already fully imported or contains no new entries.",0
		H=E+C;I=sorted(H,key=lambda b:b.get(_h,'').lower());B.save_beverage_library(I);return _Z,f"Successfully imported {F} beverages from {A}.",F
	def delete_beverages_from_addon(C,addon_name):
		B=addon_name;N=C.get_beverage_library().get(_E,[]);D=[];H=[];O=C.load_addon_library(B)
		if O is _J:return _G,f"Could not load original {B} file for integrity check.",0,0
		S={A[_C]:A for A in O if _C in A};E=len([A for A in N if A.get(_r)==B])
		for F in N:
			P=F.get(_r)==B
			if P:
				I=_G;Q=S.get(F.get(_C))
				if Q:
					T=[_h,'bjcp','abv',_q,_u]
					for J in T:
						A=F.get(J);K=Q.get(J)
						if A=='':A=_J
						if K=='':K=_J
						if J==_q:A=int(A)if isinstance(A,str)and str(A).isdigit()else A
						if A!=K:I=_Z;break
				else:I=_Z
			if P and not I:H.append(F.get(_C))
			else:D.append(F)
		G=len(H)
		if G==0 and E>0:return _G,f"All {E} entries from {B} were edited and have been kept.",E,G
		if E==0:return _G,f"No entries from {B} found in the current library.",0,0
		if not D:D=C._get_default_beverage_library().get(_E,[])
		L=C.get_sensor_beverage_assignments();R=D[0][_C]if D else _J
		for M in range(len(L)):
			if L[M]in H:L[M]=R;C.save_sensor_beverage_assignment(M,R)
		C.save_beverage_library(D);return _Z,f"Successfully deleted {G} unedited entries from {B}.",E,G
	def delete_obsolete_local_trial_files(A):
		'Cleans up old, local trial files after switching to the online model.'
		if os.path.exists(A.trial_record_file_path):
			try:os.remove(A.trial_record_file_path);print(f"SettingsManager: Obsolete local trial file {TRIAL_RECORD_FILE} deleted.")
			except Exception as B:print(f"SettingsManager Error: Could not delete local trial file: {B}")
		if _k in A.settings:del A.settings[_k];A._save_all_settings();print('SettingsManager: Obsolete local trial lock signature deleted.')
	def _load_settings(B,force_defaults=_G):
		W='notification_settings';V='user_temp_input_c';U='velocity_mode';T='keg_definitions';S='trial_record';K=force_defaults;A={};X=B._get_default_sensor_labels();Y=B._get_default_sensor_keg_assignments();P=B._get_default_beverage_assignments();C=B._get_default_system_settings();J=B._get_default_push_notification_settings();F=B._get_default_conditional_notification_settings()
		if not K and os.path.exists(B.settings_file_path):
			try:
				with open(B.settings_file_path,'r')as Z:A=json.load(Z)
				print(f"Settings loaded from {B.settings_file_path}")
			except Exception as a:print(f"Error loading or decoding JSON from {B.settings_file_path}: {a}. Using all defaults.");A={}
		else:
			if K:print('Forcing reset to default settings.')
			else:print(f"{B.settings_file_path} not found. Creating with defaults.")
			A={}
		H=not os.path.exists(B.settings_file_path)or not A
		if S in A:del A[S]
		if _k in A:del A[_k]
		if _c not in A or not isinstance(A.get(_c,[]),list)or len(A.get(_c,[]))!=B.num_sensors:A[_c]=X
		if _M not in A or not isinstance(A.get(_M,[]),list)or len(A.get(_M,[]))!=B.num_sensors:
			A[_M]=P
			if not H:print('Settings: sensor_beverage_assignments initialized/adjusted.')
		else:
			D=A[_M];b=[A[_C]for A in B.beverage_library.get(_E,[])if _C in A]
			for L in range(len(D)):
				if D[L]not in b:D[L]=P[L]
			A[_M]=D
		if T in A:del A[T]
		c=UNASSIGNED_KEG_ID
		if _N not in A or not isinstance(A.get(_N,[]),list)or len(A.get(_N,[]))!=B.num_sensors:
			A[_N]=Y
			if not H:print('Settings: sensor_keg_assignments initialized/adjusted.')
		else:
			D=A[_N];d=B.keg_map.keys()
			for M in range(len(D)):
				if D[M]!=UNASSIGNED_KEG_ID and D[M]not in d:D[M]=c
			A[_N]=D
		if _A not in A or not isinstance(A.get(_A),dict):
			A[_A]=C
			if not H:print('Settings: system_settings initialized/adjusted.')
		else:
			G=C.copy();G.update(A[_A])
			if U in G:del G[U]
			if V in G:del G[V]
			A[_A]=G
			if A[_A].get(_W)not in[_w,_o]:A[_A][_W]=C[_W]
			I=A[_A].get(_U,B.num_sensors)
			try:I=int(I)
			except ValueError:I=B.num_sensors
			if not 1<=I<=B.num_sensors:A[_A][_U]=C[_U]
			else:A[_A][_U]=I
			if _a not in A[_A]:A[_A][_a]=C[_a]
			if _Q not in A[_A]or A[_A][_Q]not in[_s,_p]:A[_A][_Q]=C[_Q]
			if _F not in A[_A]or not isinstance(A.get(_F,[]),list)or len(A[_A].get(_F,[]))!=B.num_sensors:A[_A][_F]=C[_F]
			else:
				try:A[_A][_F]=[float(A)for A in A[_A][_F]]
				except(ValueError,TypeError):A[_A][_F]=C[_F]
			if _H not in A[_A]:A[_A][_H]=C[_H]
			else:
				try:A[_A][_H]=int(A[_A][_H])
				except(ValueError,TypeError):A[_A][_H]=C[_H]
			if _I not in A[_A]:A[_A][_I]=C[_I]
			else:
				try:A[_A][_I]=int(A[_A][_I])
				except(ValueError,TypeError):A[_A][_I]=C[_I]
			if _O not in A[_A]or not isinstance(A[_A][_O],str):A[_A][_O]=C[_O]
			if _K not in A[_A]:A[_A][_K]=C[_K]
			else:
				try:A[_A][_K]=float(A[_A][_K])
				except(ValueError,TypeError):A[_A][_K]=C[_K]
		N={}
		if W in A:print("Settings: Migrating old 'notification_settings' to 'push_notification_settings'.");N=A.pop(W)
		elif _d in A:N=A.pop(_d)
		E=J.copy();E.update(N);A[_d]=E
		if E.get(_S)not in[_j,'Email','Text','Both']:E[_S]=J[_S]
		if E.get(_V)not in[_x,_m,_y,_z]:E[_V]=J[_V]
		try:Q=E.get(_L,J[_L]);E[_L]=int(Q)if str(Q).strip().isdigit()else''
		except ValueError:E[_L]=''
		if _B not in A or not isinstance(A.get(_B),dict):
			A[_B]=F
			if not H:print('Settings: conditional_notification_settings initialized/adjusted.')
		O=F.copy()
		if _B in A:O.update(A[_B])
		A[_B]=O
		if len(A[_B].get(_R,[]))!=B.num_sensors:A[_B][_R]=[_G]*B.num_sensors
		if _T not in A[_B]or not isinstance(A[_B][_T],list):A[_B][_T]=[]
		if _D not in A[_B]or not isinstance(A.get(_B,{}).get(_D),dict):A[_B][_D]=F[_D]
		else:R=F[_D].copy();R.update(O.get(_D,{}));A[_B][_D]=R
		try:A[_B][_e]=float(A[_B][_e]);A[_B][_f]=float(A[_B][_f]);A[_B][_g]=float(A[_B][_g])
		except(ValueError,TypeError):print('Settings: Conditional notification thresholds corrupted. Resetting to defaults.');A[_B][_e]=F[_e];A[_B][_f]=F[_f];A[_B][_g]=F[_g]
		if K or H:B._save_all_settings(current_settings=A)
		return A
	def reset_all_settings_to_defaults(A):print('SettingsManager: Resetting all settings to their default values.');A.beverage_library=A._get_default_beverage_library();A._save_beverage_library(A.beverage_library);A.keg_library={_P:A._get_default_keg_definitions()};A.keg_map={A[_C]:A for A in A.keg_library[_P]};A._save_keg_library(A.keg_library);A.delete_obsolete_local_trial_files();A.settings={_c:A._get_default_sensor_labels(),_N:A._get_default_sensor_keg_assignments(),_M:A._get_default_beverage_assignments(),_A:A._get_default_system_settings(),_d:A._get_default_push_notification_settings(),_B:A._get_default_conditional_notification_settings()};A._save_all_settings();print('SettingsManager: All settings have been reset to defaults and saved.')
	def get_ui_mode(A):return A.settings.get(_A,{}).get(_Q,_s)
	def save_ui_mode(A,mode_string):
		B=mode_string
		if B in[_s,_p]:A.settings.setdefault(_A,A._get_default_system_settings())[_Q]=B;A._save_all_settings();print(f"SettingsManager: UI Mode saved to {B}.")
	def get_autostart_enabled(A):return A.settings.get(_A,{}).get(_X,A._get_default_system_settings()[_X])
	def save_autostart_enabled(A,is_enabled):B=is_enabled;A.settings.setdefault(_A,A._get_default_system_settings())[_X]=bool(B);A._save_all_settings();print(f"SettingsManager: Autostart setting saved as {B}.")
	def get_launch_workflow_on_start(A):return A.settings.get(_A,{}).get(_Y,A._get_default_system_settings()[_Y])
	def save_launch_workflow_on_start(A,is_enabled):B=is_enabled;A.settings.setdefault(_A,A._get_default_system_settings())[_Y]=bool(B);A._save_all_settings();print(f"SettingsManager: Launch workflow on start setting saved as {B}.")
	def get_license_key(A):return A.settings.get(_A,{}).get(_b,'')
	def save_license_key(A,key_string):A.settings.setdefault(_A,A._get_default_system_settings())[_b]=key_string;A._save_all_settings();print(f"SettingsManager: License key saved.")
	def get_licensing_api_url(A):return A.settings.get(_A,{}).get(_n,A._get_default_system_settings()[_n])
	def get_flow_calibration_factors(A):
		B=A._get_default_system_settings().get(_F);C=A.settings.get(_A,{}).get(_F,B)
		if len(C)!=A.num_sensors:return B
		try:return[float(A)for A in C]
		except(ValueError,TypeError):return B
	def save_flow_calibration_factors(A,factors_list):
		B=factors_list
		if len(B)==A.num_sensors:A.settings.setdefault(_A,A._get_default_system_settings())[_F]=B;A._save_all_settings();print(f"SettingsManager: Flow calibration factors saved.")
	def get_flow_calibration_settings(B):A=B._get_default_system_settings();C=B.settings.get(_A,A);return{'notes':C.get(_O,A[_O]),'to_be_poured':C.get(_K,A[_K])}
	def save_flow_calibration_settings(A,to_be_poured_value=_J,notes=_J):
		C=notes;B=to_be_poured_value;D=A.settings.setdefault(_A,A._get_default_system_settings())
		if B is not _J:
			try:D[_K]=float(B)
			except(ValueError,TypeError):print('SettingsManager Error: Invalid flow_calibration_to_be_poured format for saving.');return
		if C is not _J:D[_O]=str(C)
		A._save_all_settings();print('SettingsManager: Flow calibration notes/to_be_poured saved.')
	def get_pour_volume_settings(B):A=B._get_default_system_settings();C=B.settings.get(_A,A);return{_H:C.get(_H,A[_H]),_I:C.get(_I,A[_I])}
	def save_pour_volume_settings(C,metric_ml,imperial_oz):
		B=imperial_oz;A=metric_ml
		try:A=int(A);B=int(B)
		except(ValueError,TypeError):print('SettingsManager Error: Invalid pour volume format for saving.');return
		D=C.settings.setdefault(_A,C._get_default_system_settings());D[_H]=A;D[_I]=B;C._save_all_settings();print(f"SettingsManager: Pour volumes saved (Metric: {A} ml, Imperial: {B} oz).")
	def get_sensor_beverage_assignments(A):
		C=A._get_default_beverage_assignments();B=A.settings.get(_M,C)
		if len(B)!=A.num_sensors:B=C
		return B
	def save_sensor_beverage_assignment(A,sensor_index,beverage_id):
		C=beverage_id;B=sensor_index
		if not 0<=B<A.num_sensors:return
		if _M not in A.settings or len(A.settings.get(_M,[]))!=A.num_sensors:A.settings[_M]=A._get_default_beverage_assignments()
		A.settings[_M][B]=C;A._save_all_settings();print(f"Beverage assignment for Tap {B+1} saved: {C}.")
	def get_sensor_labels(B):
		D=B.get_sensor_beverage_assignments();E=B.get_beverage_library().get(_E,[]);F={A[_C]:A[_h]for A in E if _C in A and _h in A};A=[]
		for(G,H)in enumerate(D):
			C=F.get(H)
			if C:A.append(C)
			else:A.append(f"Tap {G+1}")
		return A
	def save_sensor_labels(A,sensor_labels_list):
		B=sensor_labels_list
		if len(B)==A.num_sensors:A.settings[_c]=B;A._save_all_settings()
	def get_conditional_notification_settings(C):
		B=C._get_default_conditional_notification_settings()
		if _B not in C.settings:C.settings[_B]=B
		E=C.settings.get(_B,{}).copy()
		for(D,G)in B.items():
			if D not in E:E[D]=G
		A=E
		if _R not in A or len(A[_R])!=C.num_sensors:A[_R]=B[_R]
		if _T not in A or not isinstance(A[_T],list):A[_T]=[]
		if _D not in A:A[_D]=B[_D]
		else:F=B[_D].copy();F.update(A[_D]);A[_D]=F
		for(D,H)in B.items():
			if D not in A:A[D]=H
		return A
	def save_conditional_notification_settings(A,new_settings):A.settings[_B]=new_settings;A._save_all_settings();print('SettingsManager: Conditional notification settings saved.')
	def update_conditional_sent_status(A,tap_index,status):
		E=status;C=tap_index;D=A.settings.get(_B,{}).copy();B=D.get(_R,[])
		if len(B)!=A.num_sensors:B=[_G]*A.num_sensors
		if 0<=C<len(B):B[C]=E;D[_R]=B;A.settings[_B]=D;A._save_all_settings();print(f"SettingsManager: Updated conditional notification sent status for tap {C+1} to {E}.")
		else:print(f"SettingsManager Error: Invalid tap index {C} for updating conditional sent status.")
	def update_temp_sent_timestamp(A,timestamp=_J):B=timestamp;C=A.settings.get(_B,{}).copy();D=[B if B is not _J else time.time()];C[_T]=D;A.settings[_B]=C;A._save_all_settings();print('SettingsManager: Updated conditional temperature sent timestamp.')
	def update_error_reported_time(A,error_type,timestamp):
		D=error_type;B=A.settings.get(_B,{}).copy();C=B.get(_D,{})
		if D in C:C[D]=timestamp;B[_D]=C;A.settings[_B]=B;A._save_all_settings()
	def get_error_reported_time(A,error_type):B=A.settings.get(_B,{});return B.get(_D,{}).get(error_type,.0)
	def get_sensor_keg_assignments(B):
		D=B._get_default_sensor_keg_assignments();A=B.settings.get(_N,D)
		if len(A)!=B.num_sensors:A=D
		E=UNASSIGNED_KEG_ID;F=B.keg_map.keys()
		for C in range(len(A)):
			if A[C]!=UNASSIGNED_KEG_ID and A[C]not in F:A[C]=E
		return A
	def save_sensor_keg_assignment(A,sensor_index,keg_id):
		C=sensor_index;B=keg_id
		if not 0<=C<A.num_sensors:return
		if B!=UNASSIGNED_KEG_ID and B not in A.keg_map:return
		if _N not in A.settings or len(A.settings.get(_N,[]))!=A.num_sensors:A.settings[_N]=A._get_default_sensor_keg_assignments()
		A.settings[_N][C]=B;A._save_all_settings();print(f"Keg assignment for Tap {C+1} saved to Keg ID: {B}.")
	def get_display_units(A):return A.settings.get(_A,{}).get(_W,A._get_default_system_settings()[_W])
	def save_display_units(A,unit_system):
		B=unit_system
		if B in[_w,_o]:A.settings.setdefault(_A,A._get_default_system_settings())[_W]=B
		A._save_all_settings()
	def get_displayed_taps(B):
		D=B.settings.get(_A,{});C=B._get_default_system_settings()[_U];A=D.get(_U,C)
		try:A=int(A)
		except ValueError:A=C
		return max(1,min(A,B.num_sensors))
	def save_displayed_taps(A,number_of_taps):
		B=number_of_taps
		if isinstance(B,int)and 1<=B<=A.num_sensors:A.settings.setdefault(_A,A._get_default_system_settings())[_U]=B;A._save_all_settings()
	def get_push_notification_settings(C):
		A=C.settings.get(_d,{}).copy();D=C._get_default_push_notification_settings()
		for(E,F)in D.items():
			if E not in A:A[E]=F
		B=A.get(_L)
		if isinstance(B,str)and B.strip().isdigit():A[_L]=int(B)
		elif not isinstance(B,int)and B!='':A[_L]=D[_L]
		return A
	def save_push_notification_settings(C,new_notif_settings):
		A=new_notif_settings;B=C._get_default_push_notification_settings()
		for D in B.keys():
			if D not in A:A[D]=B[D]
		if A.get(_S)not in[_j,'Email','Text','Both']:A[_S]=B[_S]
		if A.get(_V)not in[_x,_m,_y,_z]:A[_V]=B[_V]
		try:E=str(A.get(_L,B[_L])).strip();A[_L]=int(E)if E else''
		except ValueError:A[_L]=''
		C.settings[_d]=A;C._save_all_settings();print('Push Notification settings saved.')
	def set_ds18b20_ambient_sensor(A,ambient_id):B=ambient_id;C=A.settings.get(_A,A._get_default_system_settings());C[_a]=B;A.settings[_A]=C;A._save_all_settings();print(f"SettingsManager: DS18B20 ambient sensor assignment saved: Ambient ID={B}")
	def get_ds18b20_ambient_sensor(A):B=A.settings.get(_A,A._get_default_system_settings());return{'ambient':B.get(_a,_t)}
	def get_system_settings(C):
		B=C._get_default_system_settings();A=C.settings.get(_A,B).copy()
		if _Q not in A:A[_Q]=B[_Q]
		if _b not in A:A[_b]=B[_b]
		if _X not in A:A[_X]=B[_X]
		if _Y not in A:A[_Y]=B[_Y]
		if _F not in A:A[_F]=B[_F]
		if _H not in A:A[_H]=B[_H]
		if _I not in A:A[_I]=B[_I]
		if _O not in A:A[_O]=B[_O]
		if _K not in A:A[_K]=B[_K]
		return A
	def _save_all_settings(A,current_settings=_J):
		B=current_settings;C=B if B is not _J else A.settings
		try:
			with open(A.settings_file_path,'w')as D:json.dump(C,D,indent=4)
			print(f"Settings saved to {A.settings_file_path}.")
		except Exception as E:print(f"Error saving all settings to {A.settings_file_path}: {E}")