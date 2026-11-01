import pdb
import sys
import shutil
import os
import math
from datetime import datetime
import subprocess

print("TODO: need proberes_has_b_frames code. This is on by default.")
if (len(sys.argv)<5):
    print("Usage: invideo.mkv outvideo.mkv MM:SS MM:SS 2 1")
    print("options:")
    print(" -a 2: fade in duration")
    print(" -b 1: fade out duration")
    print(" -c: skip audio filters")
    print(" -d: do not use heuristic formula/start_time additions")
    print(" -e 24: noise reduction value")
    print(" -f 20: amplification value (in dB)")
    print(" -g: keep work directory")
    quit()

arg_invideo=sys.argv[1]
arg_outvideo=sys.argv[2]
arg_starttime=sys.argv[3]
arg_endtime=sys.argv[4]

opt_infadeduration=2
opt_outfadeduration=1
opt_skipaudio=False
opt_useheuristicformula=True
opt_noisereduction=24
opt_amplification=20
opt_keepworkdir=False

optindex=5

while optindex<len(sys.argv):
    match sys.argv[optindex][0]:
        case '-':
            if (len(sys.argv[optindex])<2):
                print("Bad option length given: "+sys.argv[optindex])
                quit()
            match sys.argv[optindex][1]:
                case 'a':
                    optindex+=1
                    if (optindex>=len(sys.argv)):
                        print("Option args missing: "+sys.argv[optindex-1])
                        quit()
                    opt_infadeduration=sys.argv[optindex]
                case 'b':
                    optindex+=1
                    if (optindex>=len(sys.argv)):
                        print("Option args missing: "+sys.argv[optindex-1])
                        quit()
                    opt_outfadeduration=sys.argv[optindex]
                case 'c':
                    opt_skipaudio=True
                case 'd':
                    opt_useheuristicformula=False
                case 'e':
                    optindex+=1
                    if (optindex>=len(sys.argv)):
                        print("Option args missing: "+sys.argv[optindex-1])
                        quit()
                    opt_noisereduction=sys.argv[optindex]
                case 'f':
                    optindex+=1
                    if (optindex>=len(sys.argv)):
                        print("Option args missing: "+sys.argv[optindex-1])
                        quit()
                    opt_amplification=sys.argv[optindex]
                case 'g':
                    opt_keepworkdir=True
                case _:
                    print("Invalid option: "+sys.argv[optindex])
                    quit()
        case _:
            print("Invalid option: "+sys.argv[optindex])
            quit()
    optindex+=1

#------


# CONSTANTS
WORKFOLDER="ff_workfiles"
CONCATFILE_PATH=WORKFOLDER+"/input_mkv.txt"
KEYFRAMEFILE_PATH=WORKFOLDER+"/keyframes_all.txt"
KEYFRAMEFILE_I_PATH=WORKFOLDER+"/keyframes_i.txt"
PROBESTARTFILE_PATH=WORKFOLDER+"/probestart.txt"
PROBEBFRAMESFILE_PATH=WORKFOLDER+"/probebframes.txt"
FFMPEG_PATH="ffmpeg"
FFPROBE_PATH="ffprobe"

#------

extension_use=os.path.splitext(arg_invideo)[1]

#------

# filenames of work files

vid_audioadjust="vid_audioadjust"+extension_use
vidpiece_a="vidpiece_a"+extension_use
vidpiece_b="vidpiece_b"+extension_use
vidpiece_c="vidpiece_c"+extension_use
vidpiece_a_withfades="vidpiece_a_withfades"+extension_use
vidpiece_c_withfades="vidpiece_c_withfades"+extension_use
vid_combined="vid_combined"+extension_use

#------

vid_audioadjust_path=WORKFOLDER+"/"+vid_audioadjust
vidpiece_a_path=WORKFOLDER+"/"+vidpiece_a
vidpiece_b_path=WORKFOLDER+"/"+vidpiece_b
vidpiece_c_path=WORKFOLDER+"/"+vidpiece_c
vidpiece_a_withfades_path=WORKFOLDER+"/"+vidpiece_a_withfades
vidpiece_c_withfades_path=WORKFOLDER+"/"+vidpiece_c_withfades
vid_combined_path=WORKFOLDER+"/"+vid_combined

#------

def get_closest_next_index(arr,num):
    for i,a in enumerate(arr):
        if (a>num):
            break
    return i

heuristic_val = math.floor(3*1000000/23)
def apply_heuristic_formula_add(num):
    if (not opt_useheuristicformula):
        return num

    # if par->video_delay (typically set when video has bframes)
    if (proberes_has_b_frames):
        num += heuristic_val

    # subtract stream start time
    num -= proberes_starttime

    return num

def apply_heuristic_formula_sub(num):
    if (not opt_useheuristicformula):
        return num

    # add stream start time
    num += proberes_starttime

    # if par->video_delay (typically set when video has bframes)
    if (proberes_has_b_frames):
        num -= heuristic_val

    return num

def convert_from_micro_to_milli_with_round(num):
    micro_frac=num%1000 
    milli=math.floor(num/1000)
    if (micro_frac>=500):
        milli+=1
    return milli

def addmillidecimal(num):
    if (num==0):
        return "0.000"
    num=str(num)
    dig_a=num[:-3]
    dig_b=num[-3:]
    num=(dig_a if dig_a else '0')+'.'+(dig_b if dig_b else '0')
    return num

def do_vid_convert_ts_addheuristic(num):
    num = apply_heuristic_formula_add(num)
    num = convert_from_micro_to_milli_with_round(num)
    return addmillidecimal(num)

def do_vid_roundtomilli(num):
    #num = apply_heuristic_formula_add(num)
    num = convert_from_micro_to_milli_with_round(num)
    return addmillidecimal(num)

def do_vid_convert_ts_subheuristic(num):
    num = apply_heuristic_formula_sub(num)
    num = convert_from_micro_to_milli_with_round(num)
    return addmillidecimal(num)

#------


# start

# new work directory

shutil.rmtree(WORKFOLDER,ignore_errors=True) # remove work folder
os.makedirs(WORKFOLDER)

# create concat file for ffmpeg
lines_concat=["file "+vidpiece_a_withfades,"file "+vidpiece_b,"file "+vidpiece_c_withfades]
with open(CONCATFILE_PATH,"w") as f:
    for l in lines_concat:
        f.write(l+"\n")

# parse start time
parsed_time=datetime.strptime(arg_starttime,"%M:%S")
timestart_seconds=(parsed_time.minute*60)+parsed_time.second
timestart_microseconds=timestart_seconds*1000000;

# parse end time
parsed_time=datetime.strptime(arg_endtime,"%M:%S")
timeend_seconds=(parsed_time.minute*60)+parsed_time.second
timeend_microseconds=timeend_seconds*1000000;

print("start time (sec):"+str(timestart_seconds))
print("end time (sec):"+str(timeend_seconds))

# get keyframe list
print("Generating full keyframe list...")
with open(KEYFRAMEFILE_PATH,"w") as f:
    result=subprocess.call([FFPROBE_PATH,"-hide_banner","-loglevel","error","-select_streams","v:0","-show_entries","packet=pts_time,flags","-of","csv=print_section=0",arg_invideo],stdout=f)
    if (result):
        quit()

print("Generating I keyframe list...")
with open(KEYFRAMEFILE_I_PATH,"w") as f:
    result=subprocess.call(["awk -F',' '/K/ {print $1}' "+KEYFRAMEFILE_PATH],stdout=f,shell=True)
    if (result):
        quit()

print("Obtaining start_time (audio stream)...")
with open(PROBESTARTFILE_PATH,"w") as f:
    result=subprocess.call([FFPROBE_PATH,"-hide_banner","-loglevel","error","-select_streams","a:0","-show_entries","stream=start_time","-of","csv=print_section=0",arg_invideo],stdout=f)
    if (result):
        quit()

#print("Obtaining has_b_frames...")
#with open(PROBEBFRAMESFILE_PATH,"w") as f:
#    result=subprocess.call([FFPROBE_PATH,"-hide_banner","-loglevel","error","-select_streams","v:0","-show_entries","stream=has_b_frames","-of","csv=print_section=0",arg_invideo],stdout=f)
#    if (result):
#        quit()


# read keyframe values
iframe_ts=[]
with open(KEYFRAMEFILE_I_PATH,"r") as f:
        for l in f:
            #assuming number with 6 decimal places
            n=l.strip()
            n=n.replace('.','')
            n=int(n)
            iframe_ts.append(n)

# read start_time val 
proberes_starttime=0
with open(PROBESTARTFILE_PATH,"r") as f:
        for l in f:
            n=l.strip()
            n=n.replace('.','')
            n=int(n)
            proberes_starttime=n
print("start_time: "+str(proberes_starttime))

# read has_b_frames val
proberes_has_b_frames=True

#

print("keyframe count")
print(len(iframe_ts))

# start time (vid a)

i = get_closest_next_index(iframe_ts,timestart_microseconds)
i-=1 # index before time
vida_start=do_vid_convert_ts_addheuristic(iframe_ts[i])
print("vida start time: "+vida_start+", keyframe found (previous): "+do_vid_roundtomilli(iframe_ts[i]))

vida_start_diff=timestart_microseconds-iframe_ts[i]
if (vida_start_diff<0):
	print("WARNING: negative")
vida_start_diff=do_vid_roundtomilli(vida_start_diff)
print("start position of fade: "+vida_start_diff)

# end time (vid a)

infadeduration_microseconds=int(opt_infadeduration)*1000000
vida_end=timestart_microseconds+infadeduration_microseconds
i = get_closest_next_index(iframe_ts,vida_end)
vidb_start=do_vid_convert_ts_addheuristic(iframe_ts[i])
vida_end=do_vid_convert_ts_subheuristic(iframe_ts[i]) 
#vida_end=do_vid_roundtomilli(iframe_ts[i]) 
print("vida end time: "+vida_end)
print("vidb start time: "+vidb_start+", keyframe found (previous): "+do_vid_roundtomilli(iframe_ts[i]))

# end time (vid c)

vidc_end=do_vid_roundtomilli(timeend_microseconds)
print("vidc end time: "+vidc_end)

# start time (vid c)/end time (vid b)

outfadeduration_microseconds=int(opt_outfadeduration)*1000000
timeend_start_microseconds=timeend_microseconds-outfadeduration_microseconds
i = get_closest_next_index(iframe_ts,timeend_start_microseconds)
i-=1
vidc_start=do_vid_convert_ts_addheuristic(iframe_ts[i])
#vidb_end=do_vid_roundtomilli(iframe_ts[i])
vidb_end=do_vid_convert_ts_subheuristic(iframe_ts[i])
print("vidc start time: "+vidc_start+", keyframe found (previous): "+do_vid_roundtomilli(iframe_ts[i]))
print("vidb end time: "+vidb_end)

vidc_vidend=timeend_microseconds-iframe_ts[i]
vidc_vidend=do_vid_roundtomilli(vidc_vidend)

vidc_fadestart=timeend_start_microseconds-iframe_ts[i]
if (vidc_fadestart<0):
	print("WARNING: negative")
vidc_fadestart=do_vid_roundtomilli(vidc_fadestart)

vidc_fadeduration=do_vid_roundtomilli(outfadeduration_microseconds)

vida_fadestart=do_vid_roundtomilli(0)
vida_fadeduration=do_vid_roundtomilli(infadeduration_microseconds)

#####
#TEMP VALS

#####

print("vida: -ss "+vida_start+" -to "+vida_end)
print("vidb: -ss "+vidb_start+" -to "+vidb_end)
print("vidc: -ss "+vidc_start+" -to "+vidc_end)
print("fades for vida: st="+vida_fadestart+":d="+vida_fadeduration)
print("fades for vidc: st="+vidc_fadestart+":d="+vidc_fadeduration)

#####

vidin_use=arg_invideo

# do extractions 

print("extract first portion")
result=subprocess.call([FFMPEG_PATH,"-hide_banner","-ss", vida_start,"-to",vida_end,"-i",vidin_use,"-c","copy","-y",vidpiece_a_path])
if (result):
    quit()

print("extract middle portion")
result=subprocess.call([FFMPEG_PATH,"-hide_banner","-ss", vidb_start,"-to",vidb_end,"-i",vidin_use,"-c","copy","-y",vidpiece_b_path])
if (result):
    quit()

print("extract last portion")
result=subprocess.call([FFMPEG_PATH,"-hide_banner","-ss", vidc_start,"-to",vidc_end,"-i",vidin_use,"-c","copy","-y",vidpiece_c_path])
if (result):
    quit()

# do fades

print("do fade for first portion")
result=subprocess.call([FFMPEG_PATH,"-hide_banner","-i", vidpiece_a_path,"-ss","0","-to","100","-vf","fade=t=in:st="+vida_fadestart+":d="+vida_fadeduration,"-c:a","copy","-y",vidpiece_a_withfades_path])
if (result):
    quit()

print("do fade for last portion")
result=subprocess.call([FFMPEG_PATH,"-hide_banner","-i", vidpiece_c_path,"-ss","0","-to",vidc_vidend,"-vf","fade=t=out:st="+vidc_fadestart+":d="+vidc_fadeduration,"-c:a","copy","-y",vidpiece_c_withfades_path])
if (result):
    quit()

# rejoin

print("rejoin")
result=subprocess.call([FFMPEG_PATH,"-hide_banner","-f", "concat","-i",CONCATFILE_PATH,"-c","copy","-y",vid_combined_path])
if (result):
    quit()

# do audio 

print("adjust audio (longest operation)")
if opt_skipaudio:
    shutil.copy(vid_combined_path,arg_outvideo)
else:
    #result=subprocess.call([FFMPEG_PATH,"-hide_banner","-i", vid_combined_path,"-af","volume="+str(opt_amplification)+"dB,afftdn=nr="+str(opt_noisereduction)+",treble=g=12:f=3000","-c:v","copy","-y",arg_outvideo])
    result=subprocess.call([FFMPEG_PATH,"-hide_banner","-i", vid_combined_path,"-af","volume="+str(opt_amplification)+"dB,afftdn=nr="+str(opt_noisereduction),"-c:v","copy","-y",arg_outvideo])
    if (result):
        quit()

# remove directories
if (not opt_keepworkdir):
    shutil.rmtree(WORKFOLDER,ignore_errors=True) # remove work folder

print("success")
