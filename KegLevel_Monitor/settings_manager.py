_A2='BJCP 2021 Library'
_A1='description'
_A0='unassigned'
_z='full'
_y='source_library'
_x='starting_volume_liters'
_w='ibu'
_v='lite'
_u='metric'
_t='licensing_api_url'
_s='Daily'
_r='trial_lock_signature'
_q='imap_port'
_p='None'
_o='smtp_server'
_n='maximum_full_volume_liters'
_m='starting_total_weight_kg'
_l='status_request_settings'
_k='name'
_j='high_temp_f'
_i='low_temp_f'
_h='threshold_liters'
_g='calculated_starting_volume_liters'
_f='tare_weight_kg'
_e='push_notification_settings'
_d='sensor_labels'
_c='license_key'
_b='ds18b20_ambient_sensor'
_a='current_dispensed_liters'
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
_P='flow_calibration_notes'
_O='sensor_keg_assignments'
_N='sensor_beverage_assignments'
_M='kegs'
_L='flow_calibration_to_be_poured'
_K=None
_J='imperial_pour_oz'
_I='metric_pour_ml'
_H='flow_calibration_factors'
_G=False
_F='beverages'
_E='error_reported_times'
_D='smtp_port'
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
except ImportError:FLOW_SENSOR_PINS=[5,6,12,13,16,25,26,7,20,21];DEFAULT_K_FACTOR=51e2
class SettingsManager:
	def _get_default_sensor_labels(A):return[f"Tap {A+1}"for A in range(A.num_sensors)]
	def _get_default_keg_definitions(C):
		B=[]
		for D in range(5):A={_C:str(uuid.uuid4()),'title':f"Keg {D+1:02}",_f:4.5,_m:23.5,_n:18.93,_g:18.9,_a:.0};A[_g]=C._calculate_volume_from_weight(A[_m],A[_f]);B.append(A)
		return B
	def _get_default_sensor_keg_assignments(A):return[UNASSIGNED_KEG_ID]*A.num_sensors
	def _get_default_beverage_assignments(A):B=A._get_default_beverage_library().get(_F,[]);C=B[0][_C]if B else _K;return[C]*A.num_sensors
	def _get_default_push_notification_settings(A):return{_S:_p,_V:_s,'server_email':'','server_password':'','email_recipient':'',_o:'',_D:'','sms_number':'','sms_carrier_gateway':''}
	def _get_default_status_request_settings(A):return{'enable_status_request':_G,'authorized_sender':'','rpi_email_address':'','rpi_email_password':'','imap_server':'',_q:'',_o:'',_D:''}
	def _get_default_conditional_notification_settings(A):return{_S:_p,_h:4.,_R:[_G]*A.num_sensors,_i:35.,_j:45.,_T:[],_E:{'push':0,'volume':0,'temperature':0}}
	def _get_default_system_settings(A):return{_W:_u,_U:5,_b:_A0,_Q:_v,_c:'',_X:_G,_Y:_G,_H:[DEFAULT_K_FACTOR]*A.num_sensors,_I:355,_J:12,_P:'',_L:5e2,_t:'https://us-central1-keglevel-licensing-api.cloudfunctions.net/handle_licensing'}
	def _get_default_beverage_library(A):return{_F:[{_C:str(uuid.uuid4()),_k:'House Pale Ale','bjcp':'18(b)','abv':'5.0',_w:35,_A1:'A refreshing, hop-forward American Pale Ale with a balanced malt background and a clean, dry finish. Our go-to beer.'}]}
	def _calculate_volume_from_weight(B,total_weight_kg,empty_weight_kg,density=1.):A=total_weight_kg-empty_weight_kg;return max(.0,A/density)
	def _calculate_weight_from_volume(B,volume_liters,empty_weight_kg,density=1.):A=volume_liters*density;return empty_weight_kg+A
	def __init__(A,num_sensors_expected):
		B=os.path.dirname(os.path.abspath(__file__));print(f"SettingsManager: Using script path: {B}");A.base_dir=B;A.settings_file_path=os.path.join(A.base_dir,SETTINGS_FILE);A.beverages_file_path=os.path.join(A.base_dir,BEVERAGES_FILE);A.process_flow_file_path=os.path.join(A.base_dir,PROCESS_FLOW_FILE);A.keg_library_file_path=os.path.join(A.base_dir,KEG_LIBRARY_FILE);A.trial_record_file_path=os.path.join(A.base_dir,TRIAL_RECORD_FILE);A.bjcp_2021_file_path=os.path.join(A.base_dir,BJCP_2021_FILE);A.num_sensors=num_sensors_expected;A.beverage_library=A._load_beverage_library();A.keg_library,A.keg_map=A._load_keg_library();A.settings=A._load_settings()
		if os.path.exists(A.trial_record_file_path):A.delete_obsolete_local_trial_files()
	def get_base_dir(A):return A.base_dir
	def _load_keg_library(C):
		G='empty_weight_kg';D=C._get_default_keg_definitions()
		if os.path.exists(C.keg_library_file_path):
			try:
				with open(C.keg_library_file_path,'r')as H:
					B=json.load(H)
					if not isinstance(B.get(_M),list)or not B.get(_M):print(f"Keg Library: Contents corrupted or empty. Using default.");B={_M:D}
					I=B.get(_M,[]);F=[];E=C._get_default_keg_definitions()[0]
					for A in I:
						if G in A:A[_f]=A.pop(G)
						if _x in A:A[_g]=A.pop(_x)
						if _n not in A:A[_n]=E[_n]
						A.setdefault(_f,E[_f]);A.setdefault(_m,E[_m]);A.setdefault(_g,E[_g]);A.setdefault(_a,E[_a]);F.append(A)
					B[_M]=F;J={A[_C]:A for A in F if _C in A};return B,J
			except Exception as K:print(f"Keg Library: Error loading or decoding JSON: {K}. Using default.");return{_M:D},{A[_C]:A for A in D}
		else:print(f"{KEG_LIBRARY_FILE} not found. Creating with defaults.");B={_M:D};C._save_keg_library(B);return B,{A[_C]:A for A in D}
	def _save_keg_library(A,library):
		try:
			with open(A.keg_library_file_path,'w')as B:json.dump(library,B,indent=4)
			print(f"Keg Library saved to {A.keg_library_file_path}.")
		except Exception as C:print(f"Error saving keg library: {C}")
	def get_keg_definitions(A):A.keg_library,A.keg_map=A._load_keg_library();return A.keg_library.get(_M,[])
	def save_keg_definitions(A,definitions_list):
		B=definitions_list
		if not B:B=A._get_default_keg_definitions()
		A.keg_library[_M]=B;A.keg_map={A[_C]:A for A in B};A._save_keg_library(A.keg_library);print('Keg definitions saved.')
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
			A.keg_map[B][_a]=C
			for D in A.keg_library[_M]:
				if D.get(_C)==B:D[_a]=C;break
			return _Z
		return _G
	def save_all_keg_dispensed_volumes(A):A._save_keg_library(A.keg_library)
	def get_keg_by_id(B,keg_id):
		A=keg_id
		if A==UNASSIGNED_KEG_ID:return{_C:UNASSIGNED_KEG_ID,'title':'Offline',_x:.0,_a:.0}
		return B.keg_map.get(A)
	def _load_beverage_library(A):
		if os.path.exists(A.beverages_file_path):
			try:
				with open(A.beverages_file_path,'r')as D:
					B=json.load(D)
					if not isinstance(B.get(_F),list):print(f"Beverage Library: Error loading library. Contents corrupted. Using default.");B={_F:A._get_default_beverage_library().get(_F,[])}
					return B
			except Exception as E:print(f"Beverage Library: Error loading or decoding JSON: {E}. Using default.");return{_F:A._get_default_beverage_library().get(_F,[])}
		else:print(f"{BEVERAGES_FILE} not found. Creating with defaults.");C=A._get_default_beverage_library();A._save_beverage_library(C);return C
	def _save_beverage_library(A,library):
		try:
			with open(A.beverages_file_path,'w')as B:json.dump(library,B,indent=4)
			print(f"Beverage Library saved to {A.beverages_file_path}.")
		except Exception as C:print(f"Error saving beverage library: {C}")
	def get_beverage_library(A):return A.beverage_library
	def save_beverage_library(A,new_library_list):A.beverage_library[_F]=new_library_list;A._save_beverage_library(A.beverage_library)
	def get_available_addon_libraries(D):
		G='_library.json';E=D.get_base_dir();C=[];F={os.path.basename(D.bjcp_2021_file_path):_A2}
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
		if B==_A2:return A.bjcp_2021_file_path
		else:C=B.lower().replace(' ','_');return os.path.join(A.get_base_dir(),f"{C}_library.json")
	def load_addon_library(D,addon_name):
		A=addon_name;B=D.get_addon_filename_from_display_name(A)
		if os.path.exists(B):
			try:
				with open(B,'r',encoding='utf-8')as E:
					C=json.load(E)
					if not isinstance(C.get(_F),list):print(f"Addon Library: Contents of {A} corrupted. Aborting import.");return
					for F in C.get(_F,[]):F[_y]=A
					return C.get(_F,[])
			except Exception as G:print(f"Addon Library: Error loading or decoding JSON for {A}: {G}.");return
		else:print(f"Addon Library: {A} file not found at {B}.");return
	def import_beverages_from_addon(B,addon_name):
		A=addon_name;D=B.load_addon_library(A)
		if D is _K:return _G,f"Could not load {A} file.",0
		E=B.get_beverage_library().get(_F,[]);G={A[_C]for A in E if _C in A};C=[A for A in D if A.get(_C)not in G];F=len(C)
		if not C:return _G,f"{A} is already fully imported or contains no new entries.",0
		H=E+C;I=sorted(H,key=lambda b:b.get(_k,'').lower());B.save_beverage_library(I);return _Z,f"Successfully imported {F} beverages from {A}.",F
	def delete_beverages_from_addon(C,addon_name):
		B=addon_name;N=C.get_beverage_library().get(_F,[]);D=[];H=[];O=C.load_addon_library(B)
		if O is _K:return _G,f"Could not load original {B} file for integrity check.",0,0
		S={A[_C]:A for A in O if _C in A};E=len([A for A in N if A.get(_y)==B])
		for F in N:
			P=F.get(_y)==B
			if P:
				I=_G;Q=S.get(F.get(_C))
				if Q:
					T=[_k,'bjcp','abv',_w,_A1]
					for J in T:
						A=F.get(J);K=Q.get(J)
						if A=='':A=_K
						if K=='':K=_K
						if J==_w:A=int(A)if isinstance(A,str)and str(A).isdigit()else A
						if A!=K:I=_Z;break
				else:I=_Z
			if P and not I:H.append(F.get(_C))
			else:D.append(F)
		G=len(H)
		if G==0 and E>0:return _G,f"All {E} entries from {B} were edited and have been kept.",E,G
		if E==0:return _G,f"No entries from {B} found in the current library.",0,0
		if not D:D=C._get_default_beverage_library().get(_F,[])
		L=C.get_sensor_beverage_assignments();R=D[0][_C]if D else _K
		for M in range(len(L)):
			if L[M]in H:L[M]=R;C.save_sensor_beverage_assignment(M,R)
		C.save_beverage_library(D);return _Z,f"Successfully deleted {G} unedited entries from {B}.",E,G
	def delete_obsolete_local_trial_files(A):
		'Cleans up old, local trial files after switching to the online model.'
		if os.path.exists(A.trial_record_file_path):
			try:os.remove(A.trial_record_file_path);print(f"SettingsManager: Obsolete local trial file {TRIAL_RECORD_FILE} deleted.")
			except Exception as B:print(f"SettingsManager Error: Could not delete local trial file: {B}")
		if _r in A.settings:del A.settings[_r];A._save_all_settings();print('SettingsManager: Obsolete local trial lock signature deleted.')
	def _load_settings(B,force_defaults=_G):
		Z='notification_settings';Y='user_temp_input_c';X='velocity_mode';W='keg_definitions';V='trial_record';N=force_defaults;A={};a=B._get_default_sensor_labels();b=B._get_default_sensor_keg_assignments();T=B._get_default_beverage_assignments();C=B._get_default_system_settings();I=B._get_default_push_notification_settings();c=B._get_default_status_request_settings();F=B._get_default_conditional_notification_settings()
		if not N and os.path.exists(B.settings_file_path):
			try:
				with open(B.settings_file_path,'r')as d:A=json.load(d)
				print(f"Settings loaded from {B.settings_file_path}")
			except Exception as e:print(f"Error loading or decoding JSON from {B.settings_file_path}: {e}. Using all defaults.");A={}
		else:
			if N:print('Forcing reset to default settings.')
			else:print(f"{B.settings_file_path} not found. Creating with defaults.")
			A={}
		J=not os.path.exists(B.settings_file_path)or not A
		if V in A:del A[V]
		if _r in A:del A[_r]
		if _d not in A or not isinstance(A.get(_d,[]),list)or len(A.get(_d,[]))!=B.num_sensors:A[_d]=a
		if _N not in A or not isinstance(A.get(_N,[]),list)or len(A.get(_N,[]))!=B.num_sensors:
			A[_N]=T
			if not J:print('Settings: sensor_beverage_assignments initialized/adjusted.')
		else:
			E=A[_N];f=[A[_C]for A in B.beverage_library.get(_F,[])if _C in A]
			for O in range(len(E)):
				if E[O]not in f:E[O]=T[O]
			A[_N]=E
		if W in A:del A[W]
		g=UNASSIGNED_KEG_ID
		if _O not in A or not isinstance(A.get(_O,[]),list)or len(A.get(_O,[]))!=B.num_sensors:
			A[_O]=b
			if not J:print('Settings: sensor_keg_assignments initialized/adjusted.')
		else:
			E=A[_O];h=B.keg_map.keys()
			for P in range(len(E)):
				if E[P]!=UNASSIGNED_KEG_ID and E[P]not in h:E[P]=g
			A[_O]=E
		if _A not in A or not isinstance(A.get(_A),dict):
			A[_A]=C
			if not J:print('Settings: system_settings initialized/adjusted.')
		else:
			G=C.copy();G.update(A[_A])
			if X in G:del G[X]
			if Y in G:del G[Y]
			A[_A]=G
			if A[_A].get(_W)not in['imperial',_u]:A[_A][_W]=C[_W]
			K=A[_A].get(_U,B.num_sensors)
			try:K=int(K)
			except ValueError:K=B.num_sensors
			if not 1<=K<=B.num_sensors:A[_A][_U]=C[_U]
			else:A[_A][_U]=K
			if _b not in A[_A]:A[_A][_b]=C[_b]
			if _Q not in A[_A]or A[_A][_Q]not in[_z,_v]:A[_A][_Q]=C[_Q]
			if _H not in A[_A]or not isinstance(A.get(_H,[]),list)or len(A[_A].get(_H,[]))!=B.num_sensors:A[_A][_H]=C[_H]
			else:
				try:A[_A][_H]=[float(A)for A in A[_A][_H]]
				except(ValueError,TypeError):A[_A][_H]=C[_H]
			if _I not in A[_A]:A[_A][_I]=C[_I]
			else:
				try:A[_A][_I]=int(A[_A][_I])
				except(ValueError,TypeError):A[_A][_I]=C[_I]
			if _J not in A[_A]:A[_A][_J]=C[_J]
			else:
				try:A[_A][_J]=int(A[_A][_J])
				except(ValueError,TypeError):A[_A][_J]=C[_J]
			if _P not in A[_A]or not isinstance(A[_A][_P],str):A[_A][_P]=C[_P]
			if _L not in A[_A]:A[_A][_L]=C[_L]
			else:
				try:A[_A][_L]=float(A[_A][_L])
				except(ValueError,TypeError):A[_A][_L]=C[_L]
		Q={}
		if Z in A:print("Settings: Migrating old 'notification_settings' to 'push_notification_settings'.");Q=A.pop(Z)
		elif _e in A:Q=A.pop(_e)
		D=I.copy();D.update(Q);A[_e]=D
		if D.get(_S)not in[_p,'Email','Text','Both']:D[_S]=I[_S]
		if D.get(_V)not in['Hourly',_s,'Weekly','Monthly']:D[_V]=I[_V]
		R=D.get(_D,I[_D]);D.setdefault(_o,I[_o])
		try:
			L=str(R).strip()
			if L.isdigit():D[_D]=int(L)
			else:D[_D]=''
		except Exception:D[_D]=''
		i=A.pop(_l,{});H=c.copy();H.update(i);A[_l]=H
		for M in[_q,_D]:
			R=H.get(M)
			try:
				L=str(R).strip()
				if L.isdigit():H[M]=int(L)
				else:H[M]=''
			except Exception:H[M]=''
		if _B not in A or not isinstance(A.get(_B),dict):
			A[_B]=F
			if not J:print('Settings: conditional_notification_settings initialized/adjusted.')
		S=F.copy()
		if _B in A:S.update(A[_B])
		A[_B]=S
		if len(A[_B].get(_R,[]))!=B.num_sensors:A[_B][_R]=[_G]*B.num_sensors
		if _T not in A[_B]or not isinstance(A[_B][_T],list):A[_B][_T]=[]
		if _E not in A[_B]or not isinstance(A.get(_B,{}).get(_E),dict):A[_B][_E]=F[_E]
		else:U=F[_E].copy();U.update(S.get(_E,{}));A[_B][_E]=U
		try:A[_B][_h]=float(A[_B][_h]);A[_B][_i]=float(A[_B][_i]);A[_B][_j]=float(A[_B][_j])
		except(ValueError,TypeError):print('Settings: Conditional notification thresholds corrupted. Resetting to defaults.');A[_B][_h]=F[_h];A[_B][_i]=F[_i];A[_B][_j]=F[_j]
		if N or J:B._save_all_settings(current_settings=A)
		return A
	def reset_all_settings_to_defaults(A):print('SettingsManager: Resetting all settings to their default values.');A.beverage_library=A._get_default_beverage_library();A._save_beverage_library(A.beverage_library);A.keg_library={_M:A._get_default_keg_definitions()};A.keg_map={A[_C]:A for A in A.keg_library[_M]};A._save_keg_library(A.keg_library);A.delete_obsolete_local_trial_files();A.settings={_d:A._get_default_sensor_labels(),_O:A._get_default_sensor_keg_assignments(),_N:A._get_default_beverage_assignments(),_A:A._get_default_system_settings(),_e:A._get_default_push_notification_settings(),_l:A._get_default_status_request_settings(),_B:A._get_default_conditional_notification_settings()};A._save_all_settings();print('SettingsManager: All settings have been reset to defaults and saved.')
	def get_ui_mode(A):return A.settings.get(_A,{}).get(_Q,_z)
	def save_ui_mode(A,mode_string):
		B=mode_string
		if B in[_z,_v]:A.settings.setdefault(_A,A._get_default_system_settings())[_Q]=B;A._save_all_settings();print(f"SettingsManager: UI Mode saved to {B}.")
	def get_autostart_enabled(A):return A.settings.get(_A,{}).get(_X,A._get_default_system_settings()[_X])
	def save_autostart_enabled(A,is_enabled):B=is_enabled;A.settings.setdefault(_A,A._get_default_system_settings())[_X]=bool(B);A._save_all_settings();print(f"SettingsManager: Autostart setting saved as {B}.")
	def get_launch_workflow_on_start(A):return A.settings.get(_A,{}).get(_Y,A._get_default_system_settings()[_Y])
	def save_launch_workflow_on_start(A,is_enabled):B=is_enabled;A.settings.setdefault(_A,A._get_default_system_settings())[_Y]=bool(B);A._save_all_settings();print(f"SettingsManager: Launch workflow on start setting saved as {B}.")
	def get_license_key(A):return A.settings.get(_A,{}).get(_c,'')
	def save_license_key(A,key_string):A.settings.setdefault(_A,A._get_default_system_settings())[_c]=key_string;A._save_all_settings();print(f"SettingsManager: License key saved.")
	def get_licensing_api_url(A):return A.settings.get(_A,{}).get(_t,A._get_default_system_settings()[_t])
	def get_flow_calibration_factors(A):
		B=A._get_default_system_settings().get(_H);C=A.settings.get(_A,{}).get(_H,B)
		if len(C)!=A.num_sensors:return B
		try:return[float(A)for A in C]
		except(ValueError,TypeError):return B
	def save_flow_calibration_factors(A,factors_list):
		B=factors_list
		if len(B)==A.num_sensors:A.settings.setdefault(_A,A._get_default_system_settings())[_H]=B;A._save_all_settings();print(f"SettingsManager: Flow calibration factors saved.")
	def get_flow_calibration_settings(B):A=B._get_default_system_settings();C=B.settings.get(_A,A);return{'notes':C.get(_P,A[_P]),'to_be_poured':C.get(_L,A[_L])}
	def save_flow_calibration_settings(A,to_be_poured_value=_K,notes=_K):
		C=notes;B=to_be_poured_value;D=A.settings.setdefault(_A,A._get_default_system_settings())
		if B is not _K:
			try:D[_L]=float(B)
			except(ValueError,TypeError):print('SettingsManager Error: Invalid flow_calibration_to_be_poured format for saving.');return
		if C is not _K:D[_P]=str(C)
		A._save_all_settings();print('SettingsManager: Flow calibration notes/to_be_poured saved.')
	def get_pour_volume_settings(B):A=B._get_default_system_settings();C=B.settings.get(_A,A);return{_I:C.get(_I,A[_I]),_J:C.get(_J,A[_J])}
	def save_pour_volume_settings(C,metric_ml,imperial_oz):
		B=imperial_oz;A=metric_ml
		try:A=int(A);B=int(B)
		except(ValueError,TypeError):print('SettingsManager Error: Invalid pour volume format for saving.');return
		D=C.settings.setdefault(_A,C._get_default_system_settings());D[_I]=A;D[_J]=B;C._save_all_settings();print(f"SettingsManager: Pour volumes saved (Metric: {A} ml, Imperial: {B} oz).")
	def get_sensor_beverage_assignments(A):
		C=A._get_default_beverage_assignments();B=A.settings.get(_N,C)
		if len(B)!=A.num_sensors:B=C
		return B
	def save_sensor_beverage_assignment(A,sensor_index,beverage_id):
		C=beverage_id;B=sensor_index
		if not 0<=B<A.num_sensors:return
		if _N not in A.settings or len(A.settings.get(_N,[]))!=A.num_sensors:A.settings[_N]=A._get_default_beverage_assignments()
		A.settings[_N][B]=C;A._save_all_settings();print(f"Beverage assignment for Tap {B+1} saved: {C}.")
	def get_sensor_labels(B):
		D=B.get_sensor_beverage_assignments();E=B.get_beverage_library().get(_F,[]);F={A[_C]:A[_k]for A in E if _C in A and _k in A};A=[]
		for(G,H)in enumerate(D):
			C=F.get(H)
			if C:A.append(C)
			else:A.append(f"Tap {G+1}")
		return A
	def save_sensor_labels(A,sensor_labels_list):
		B=sensor_labels_list
		if len(B)==A.num_sensors:A.settings[_d]=B;A._save_all_settings()
	def get_conditional_notification_settings(C):
		B=C._get_default_conditional_notification_settings()
		if _B not in C.settings:C.settings[_B]=B
		E=C.settings.get(_B,{}).copy()
		for(D,G)in B.items():
			if D not in E:E[D]=G
		A=E
		if _R not in A or len(A[_R])!=C.num_sensors:A[_R]=B[_R]
		if _T not in A or not isinstance(A[_T],list):A[_T]=[]
		if _E not in A:A[_E]=B[_E]
		else:F=B[_E].copy();F.update(A[_E]);A[_E]=F
		for(D,H)in B.items():
			if D not in A:A[D]=H
		return A
	def save_conditional_notification_settings(A,new_settings):A.settings[_B]=new_settings;A._save_all_settings();print('SettingsManager: Conditional notification settings saved.')
	def update_conditional_sent_status(A,tap_index,status):
		E=status;C=tap_index;D=A.settings.get(_B,{}).copy();B=D.get(_R,[])
		if len(B)!=A.num_sensors:B=[_G]*A.num_sensors
		if 0<=C<len(B):B[C]=E;D[_R]=B;A.settings[_B]=D;A._save_all_settings();print(f"SettingsManager: Updated conditional notification sent status for tap {C+1} to {E}.")
		else:print(f"SettingsManager Error: Invalid tap index {C} for updating conditional sent status.")
	def update_temp_sent_timestamp(A,timestamp=_K):B=timestamp;C=A.settings.get(_B,{}).copy();D=[B if B is not _K else time.time()];C[_T]=D;A.settings[_B]=C;A._save_all_settings();print('SettingsManager: Updated conditional temperature sent timestamp.')
	def update_error_reported_time(A,error_type,timestamp):
		D=error_type;B=A.settings.get(_B,{}).copy();C=B.get(_E,{})
		if D in C:C[D]=timestamp;B[_E]=C;A.settings[_B]=B;A._save_all_settings()
	def get_error_reported_time(A,error_type):B=A.settings.get(_B,{});return B.get(_E,{}).get(error_type,.0)
	def get_sensor_keg_assignments(B):
		D=B._get_default_sensor_keg_assignments();A=B.settings.get(_O,D)
		if len(A)!=B.num_sensors:A=D
		E=UNASSIGNED_KEG_ID;F=B.keg_map.keys()
		for C in range(len(A)):
			if A[C]!=UNASSIGNED_KEG_ID and A[C]not in F:A[C]=E
		return A
	def save_sensor_keg_assignment(A,sensor_index,keg_id):
		C=sensor_index;B=keg_id
		if not 0<=C<A.num_sensors:return
		if B!=UNASSIGNED_KEG_ID and B not in A.keg_map:return
		if _O not in A.settings or len(A.settings.get(_O,[]))!=A.num_sensors:A.settings[_O]=A._get_default_sensor_keg_assignments()
		A.settings[_O][C]=B;A._save_all_settings();print(f"Keg assignment for Tap {C+1} saved to Keg ID: {B}.")
	def get_display_units(A):return A.settings.get(_A,{}).get(_W,A._get_default_system_settings()[_W])
	def save_display_units(A,unit_system):
		B=unit_system
		if B in['imperial',_u]:A.settings.setdefault(_A,A._get_default_system_settings())[_W]=B
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
		A=C.settings.get(_e,{}).copy();E=C._get_default_push_notification_settings()
		for(D,F)in E.items():
			if D not in A:A[D]=F
		B=A.get(_D)
		if isinstance(B,str):
			if B.strip().isdigit():A[_D]=int(B)
			else:A[_D]=''
		return A
	def save_push_notification_settings(C,new_notif_settings):
		A=new_notif_settings;B=C._get_default_push_notification_settings()
		for D in B.keys():
			if D not in A:A[D]=B[D]
		if A.get(_S)not in[_p,'Email','Text','Both']:A[_S]=B[_S]
		if A.get(_V)not in['Hourly',_s,'Weekly','Monthly']:A[_V]=B[_V]
		F=A.get(_D,B[_D])
		try:
			E=str(F).strip()
			if E.isdigit():A[_D]=int(E)
			else:A[_D]=''
		except Exception:A[_D]=''
		C.settings[_e]=A;C._save_all_settings();print('Push Notification settings saved.')
	def get_status_request_settings(D):
		A=D.settings.get(_l,{}).copy();E=D._get_default_status_request_settings()
		for(B,F)in E.items():
			if B not in A:A[B]=F
		for B in[_q,_D]:
			C=A.get(B)
			if isinstance(C,str)and C.strip().isdigit():A[B]=int(C.strip())
			elif not isinstance(C,int):A[B]=''
		return A
	def save_status_request_settings(C,new_status_req_settings):
		B=new_status_req_settings;D=C._get_default_status_request_settings()
		for A in D.keys():
			if A not in B:B[A]=D[A]
		for A in[_q,_D]:
			F=B.get(A)
			try:
				E=str(F).strip()
				if E.isdigit():B[A]=int(E)
				else:B[A]=''
			except Exception:B[A]=''
		C.settings[_l]=B;C._save_all_settings();print('Status Request settings saved.')
	def set_ds18b20_ambient_sensor(A,ambient_id):B=ambient_id;C=A.settings.get(_A,A._get_default_system_settings());C[_b]=B;A.settings[_A]=C;A._save_all_settings();print(f"SettingsManager: DS18B20 ambient sensor assignment saved: Ambient ID={B}")
	def get_ds18b20_ambient_sensor(A):B=A.settings.get(_A,A._get_default_system_settings());return{'ambient':B.get(_b,_A0)}
	def get_system_settings(C):
		B=C._get_default_system_settings();A=C.settings.get(_A,B).copy()
		if _Q not in A:A[_Q]=B[_Q]
		if _c not in A:A[_c]=B[_c]
		if _X not in A:A[_X]=B[_X]
		if _Y not in A:A[_Y]=B[_Y]
		if _H not in A:A[_H]=B[_H]
		if _I not in A:A[_I]=B[_I]
		if _J not in A:A[_J]=B[_J]
		if _P not in A:A[_P]=B[_P]
		if _L not in A:A[_L]=B[_L]
		return A
	def _save_all_settings(A,current_settings=_K):
		B=current_settings;C=B if B is not _K else A.settings
		try:
			with open(A.settings_file_path,'w')as D:json.dump(C,D,indent=4)
			print(f"Settings saved to {A.settings_file_path}.")
		except Exception as E:print(f"Error saving all settings to {A.settings_file_path}: {E}")