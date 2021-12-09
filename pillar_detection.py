import os
from collections import Counter
import cv2
import glob
import re
import subprocess
import argparse
import copy
import datetime
import time

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input_dir", default="./input", help="Input source vid directory")
parser.add_argument("-o", "--output_dir", default="./out", help="Output vid directory")
parser.add_argument("-c", "--crf", default=20, type=int, help="set crf level")
parser.add_argument("-sp", "--add_sharpening", default=False, action="store_true", help="add ffmpeg sharpening filter")
parser.add_argument("-lb", "--add_letterbox", default=False, action="store_true", help="add letterbox to make 16:9 ratio")
parser.add_argument("-uhd", "--uhd_output", default=False, action="store_true", help="set output resolution to 3840:2160")
parser.add_argument("-mul", "--multi_encoding", default=2, type=int, help="when log file exist, encoding mutiple videos by this args")
parser.add_argument("-s", "--cropsize_scale", default=1, type=int, help="before use crop size from logfile, scale up the crop size (for reuse when vid rescaled)")
parser.add_argument("-log", "--only_logfile", default=False, action="store_true", help="large vid mode. (only write log file.)")
parser.add_argument("-man", "--manual_mode", default=False, action="store_true", help="manual cropping without using log file (Ignore log files)")
parser.add_argument("-edit", "--edit_mode", default=False, action="store_true", help="get first crop area from log file")
parser.add_argument("-d", "--debug", default=False, action="store_true", help="for debugging. (short length video output)")
args = parser.parse_args()

# option when only write log file (no encoding) : -log
# options when only edit log file that already exists (no encoding) : -log -edit

# Adjust crop info in display layout.
def resizeCropInfo(key, cropPos, frame_width, frame_height):
    def _IsOutOfBound(_cropPos):
        w, h, x, y = _cropPos
        if (w + x) > frame_width or (h + y) > frame_height:
            return True
        if (x < 0) or (y < 0):
            return True
        if (w <= 0) or (h <= 0):
            return True
    
    w, h, x, y = cropPos
    # Left (Expand width)
    if key == ord('j') or key == ord('J'):
        x -= 2
        w += 4
    # Right (Shrink width)
    elif key == ord('l') or key == ord('L'):
        x += 2
        w -= 4
    # Up (Expand height)
    elif key == ord('i') or key == ord('I'):
        y -= 2
        h += 4
    # Down (Shrink height)
    elif key == ord('k') or key == ord('K'):
        y += 2
        h -= 4
    # Num 4 (Move left)
    elif key == ord('a') or key == ord('A'):
        # w -= 1
        x -= 1
    # Num 6 (Move right)
    elif key == ord('d') or key == ord('D'):
        # w += 1
        x += 1
    # Num 8 (Move upward)
    elif key == ord('w') or key == ord('W'):
        # h -= 1
        y -= 1
    # Num 2 (Move downward)
    elif key == ord('s') or key == ord('S'):
        # h += 1
        y += 1
    _cropPos = w, h, x, y

    if not _IsOutOfBound(_cropPos):
        cropPos = _cropPos

    return cropPos

def getTime():
    dt_now = datetime.datetime.now()
    dt_str = dt_now.strftime('[%Y-%m-%d %H:%M:%S]')
    # print(dt_str)

    return dt_str

def getVideDuration(file_path):
    ffprobe_command = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{file_path}\""
    p = subprocess.run(ffprobe_command, shell=False, stdout=subprocess.PIPE)
    _hour = 0
    _min = 0
    _sec = 0
    
    _sec = int(float(p.stdout.decode('utf-8')))
    # print(_sec)
    
    if _sec > 60 :
        _min = int(_sec // 60)
        _sec = _sec - (60 * _min)
        # print(_min, _sec)
    if _sec > 3600 : 
        _hour = int(_sec // 60)
        _sec = _sec - (60 * _min)
        _min = int(_sec // 60)
        _sec = _sec - (60 * _min)
        # print(_hour, _min, _sec)
    
    return [_hour, _min, _sec]

# for unicode free filename
def imwrite(filename, img, params=None): 
    try: 
        ext = os.path.splitext(filename)[1] 
        result, n = cv2.imencode(ext, img, params) 
        if result: 
            with open(filename, mode='w+b') as f: 
                n.tofile(f) 
                return True 
        else: 
            return False 
    except Exception as e: 
        print(e)
        return False

def main():
    vid_types = ('*.avi', '*.mov', '*.mp4', '*.mxf')

    # video encoding opts
    input_dir = args.input_dir
    crf = args.crf
    add_letterbox = args.add_letterbox
    add_sharpening = args.add_sharpening
    uhd_output = args.uhd_output

    # program modes
    multi_how_many = args.multi_encoding - 1
    scale =  int(args.cropsize_scale)
    only_logfile = args.only_logfile
    manual_mode = args.manual_mode
    debug = args.debug
    edit_mode = args.edit_mode

    if scale < 1 :
        print(f"[!!! ERROR !!!]\t Invalid scale option [scale : {scale}]")
        return
    elif multi_how_many < 0 :
        print(f"[!!! WARRNING !!!]\t \"multi_encoding\" option should be more then 1 [multi_encoding : {multi_how_many}]")
        return

    uhd_output_args = ""
    if uhd_output :
        uhd_output_args = "-s 3840x2160"

    debug_shortOutput = ""
    if debug :
        debug_shortOutput = "-t 15 -ss 30"

    output_dir = args.output_dir
    input_list = []
    for types in vid_types :
        input_list += glob.glob(os.path.join(input_dir, types))
    input_list = sorted(input_list)

    print("[INFO]\t Input dir :", input_dir)

    print(str(input_list))
    
    for vid_index, fpath in enumerate(input_list):
        vid_name = os.path.basename(fpath)[:-4]
        vid_num = len(input_list)
        isSkipped = False
        logs_dir = input_dir
        logs = ''

        print("[INFO]\t Log dir :", logs_dir)
        # Read log file if exist
        if not manual_mode:
            if not os.path.exists(f"{logs_dir}/{vid_name}.txt"):
                print(f"[INFO]\t Can`t find log file. [{logs_dir}/{vid_name}.txt]")
                edit_mode = False
            else :
                print(f"[INFO]\t Loading log file... [{logs_dir}/{vid_name}.txt]")
                f = open(f"{logs_dir}/{vid_name}.txt", "r")
                logs = f.read()

                if logs != '':
                    try :
                        # Delete "crop=" in list "crop"
                        allCrops = re.findall("crop=\S+", logs)
                        cropPos = allCrops[-1].split(":")
                        cropPos[0] = cropPos[0][5:]
                        print(f"[INFO]\t Crop area from log file: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")
                        cropPos = [int(x * scale) for x in cropPos]
                        if scale > 1 :
                            print(f"[INFO]\t Scale up crop area: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")

                    except:
                        print(f"[!!! WARNNIG !!!]\t Can`t read log file. [{logs_dir}/{vid_name}.txt]")

                else :
                    print(f"[!!! WARNNIG !!!]\t Empty log file. [{logs_dir}/{vid_name}.txt]")

        if (logs == '') or manual_mode or edit_mode:
            # TODO : Korean title text bug fix
            # vid_name = vid_name.encode('utf-8').decode('cp949')

            print(f"[INFO]\t [Video num : {vid_index + 1} / {vid_num}]")
            print("[INFO]\t File to detect crop area: ", fpath)
            if edit_mode:
                print("[INFO]\t (Edit mode) Read crop area from log file...")
                print(f"[INFO]\t Crop area from log file: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")
            else :
                print("[INFO]\t Detecting crop area...")
                p = subprocess.Popen(["ffmpeg", "-ss", "10", "-i", fpath, "-vf", "cropdetect=limit=38",
                                    "-vframes", "3000", "-f", "null", "out.null"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                infos = p.stderr.read().decode('utf-8')
                allCrops = re.findall("crop=\S+", infos)
                mostCommonCrop = Counter(allCrops).most_common(1)

                if len(mostCommonCrop) > 0 :
                    crop = mostCommonCrop[0][0]
                else :
                    print(f"[!!! ERROR !!!]\t Can`t read input vid. Skip to next vid \t ({fpath})")
                    continue

                # Delete "crop=" in list "crop"
                cropPos = crop.split(":")
                cropPos[0] = cropPos[0][5:]
                print(f"[INFO]\t Most common detected crop area: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")
                cropPos = [int(x) for x in cropPos]

            # Capture vid, Get Vid info
            capture = cv2.VideoCapture(fpath)
            frame_width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            frame_height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = capture.get(cv2.CAP_PROP_FPS)
            frame_pos = 0
            frame_count = 0
            
            # Crop Area even num check
            if (cropPos[0] % 2) != 0 :
                if (cropPos[0] + 1) >= frame_width:
                    cropPos[0] -= 1
                else:
                    cropPos[0] += 1
            if (cropPos[1] % 2) != 0 :
                if (cropPos[1] + 1) >= frame_width:
                    cropPos[1] -= 1
                else:
                    cropPos[1] += 1

            # Crop Area Multiple of 4 check
            if (cropPos[0] % 4) != 0 :
                if (cropPos[0] + 2) >= frame_width:
                    cropPos[0] -= 2
                else:
                    cropPos[0] += 2
            if (cropPos[1] % 4) != 0 :
                if (cropPos[1] + 2) >= frame_width:
                    cropPos[1] -= 2
                else:
                    cropPos[1] += 2

            key = None
            isPaused = False
            cleanFrame = None
            _boxedFrame = None
            frame = None

            cv2.namedWindow(f'{vid_name}', cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)

            # Display crop size control UI
            while True:
                key = cv2.waitKeyEx(10)

                # Close button(X button) event
                if cv2.getWindowProperty(f'{vid_name}', cv2.WND_PROP_VISIBLE) < 1 :
                    return

                if key > 0 :
                    # 13 == Enter key ASCII Code
                    if key == 13:
                        break
                    # Pause
                    elif key == ord('p') or key == ord('P'):
                        if isPaused :
                            isPaused = False
                        else :
                            isPaused = True
                            # frame = copy.deepcopy(cleanFrame)
                    # Replay
                    elif key == ord('r') or key == ord('R'):
                        if not isPaused:
                            capture = cv2.VideoCapture(fpath)
                            continue
                    # Move Forward (5s)
                    elif key == ord('e') or key == ord('E'):
                        if not isPaused:
                            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_pos + (fps * 5))
                    # Move Backward (5s)
                    elif key == ord('q') or key == ord('Q'):
                        if not isPaused:
                            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_pos - (fps * 5))
                    # Display key guide
                    elif key == ord('h') or key == ord('H'):
                        print("[INFO]\t ### KEY GUIDE ##############################################################################################################################################################")
                        print("[INFO]\t #  (MOVE : wasd), (RESIZE : ijkl), (FOR / BACKWARD : q, e), (RESET : r), (PAUSE : p), (SKIP : n), (Preview : v), (Save current frame : b)(CONFIRM : enter)  #")
                        print("[INFO]\t ############################################################################################################################################################################ ")
                    # Skip this Vid
                    elif key == ord('n') or key == ord('N'):
                        print(f"[INFO]\t Skip this video")
                        isSkipped = True
                        break
                    # Preview this crop area on new window
                    elif key == ord('v') or key == ord('V'):
                        _x = cropPos[2]
                        _y = cropPos[3]
                        _w = cropPos[0]
                        _h = cropPos[1]
                        _frame = copy.deepcopy(cleanFrame)
                        cv2.namedWindow(f'{vid_name}_current_area', cv2.WINDOW_KEEPRATIO)
                        cv2.waitKey(10)
                        cv2.imshow(f'{vid_name}_current_area', _frame[_y: (_y + _h), _x: (_x + _w)])
                    # Capture, download this crop area in png file
                    elif key == ord('b') or key == ord('B'):
                        _x = cropPos[2]
                        _y = cropPos[3]
                        _w = cropPos[0]
                        _h = cropPos[1]
                        _frame = copy.deepcopy(cleanFrame)

                        _vid_name = vid_name.replace(" ","_")
                        image_dir = "./capture_image"
                        path = os.path.join(image_dir, _vid_name)
                        if not os.path.exists(path) :
                            os.makedirs(path)
                            print(f'[INFO]\t {path} created')

                        image_name = f'{_vid_name}_({frame_pos}-{frame_count})_before.png'
                        _path = os.path.join(path, image_name)
                        imwrite(_path, _boxedFrame)
                        print(f"\n[INFO]\t Saved current frame              : {_path}")

                        image_name = f'{_vid_name}_({frame_pos}-{frame_count})_after.png'
                        _path = os.path.join(path, image_name)
                        imwrite(_path, _frame[_y: (_y + _h), _x: (_x + _w)])
                        print(f"[INFO]\t Saved current frame in crop area : {_path}")
                        
                    else:
                        # Crop Area control
                        cropPos = resizeCropInfo(key, cropPos, frame_width, frame_height)

                if not isPaused:
                    frame_pos = int(capture.get(cv2.CAP_PROP_POS_FRAMES))
                    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
                
                if(frame_pos >= frame_count):
                    break

                # When paused, hold current frame untill unpause.
                if isPaused:
                    # deep copy current frame, use that frame for draw rectangle.
                    # cleanFrame = copy.deepcopy(frame)
                    _boxedFrame = copy.deepcopy(cleanFrame)
                    cv2.rectangle(_boxedFrame, (cropPos[2], cropPos[3]), (cropPos[2] + cropPos[0],
                            cropPos[3] + cropPos[1]), (0, 0, 255), thickness=2, lineType=cv2.LINE_8)
                    cv2.imshow(f'{vid_name}', _boxedFrame)
                else :
                    ret, frame = capture.read()
                    # deep copy current frame for clean preview.
                    cleanFrame = copy.deepcopy(frame)
                    cv2.rectangle(frame, (cropPos[2], cropPos[3]), (cropPos[2] + cropPos[0],
                            cropPos[3] + cropPos[1]), (0, 0, 255), thickness=2, lineType=cv2.LINE_8)    
                    cv2.imshow(f'{vid_name}', frame)
                    _boxedFrame = copy.deepcopy(frame)

                    
                    print("[INFO]\t Current crop area : ", end="")
                    print(cropPos, end="")
                    print(f"\t Frame Count ({frame_pos}/{frame_count})\t[PRESS \"h\" TO VIEW KEY GUIDE]", end="\r") 
                    
            print("")
            capture.release()
            cv2.destroyAllWindows()

            # Debugging
            # cropPos[0] = 678
            # cropPos[1] = 402
            # cropPos[2] = 20
            # cropPos[3] = 38
            # pad_arg = ""

            dt_str = getTime()

            if not isSkipped:
                if not os.path.exists(f"{logs_dir}"):
                    print(f"[INFO]\t Make log directory [{logs_dir}/{vid_name}.txt]")
                    os.makedirs(f"{logs_dir}")

                if not os.path.exists(f"{logs_dir}/{vid_name}.txt"):
                    print(f"[INFO]\t Save log file in [{logs_dir}/{vid_name}.txt]")
                    f = open(f"{logs_dir}/{vid_name}.txt", 'w')
                else :
                    print(f"[INFO]\t Add line in log file [{logs_dir}/{vid_name}.txt]")
                    f = open(f"{logs_dir}/{vid_name}.txt", 'a')

                f.write(f"{dt_str}\tcrop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]}\n")
                f.close

        # Set ffmpeg commands, actual ffmpeg encoding
        if not (only_logfile or isSkipped):
            crop_arg = f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]}"
            print(f"[INFO]\t [CropInfo] (W : {cropPos[0]}), (H : {cropPos[1]}), (X : {cropPos[2]}), (Y : {cropPos[3]})")

            crop_arg = f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]}"
            current_crop_ratio = cropPos[0] / cropPos[1]
            scale_arg = ""
            pad_arg = ""

            """
            Set padding(letter box) argument
            variable "offset" for 16:9 output display ratio

            pad_arg syntax:
                pad= {width after padding}:{height after padding}:{x offset of pad}:{y offset of pad}
            """
            if add_letterbox :
                # Always target 16:9 display ratio
                target_ratio = 16 / 9
                print("[INFO]\t Target ratio : %.7f" %target_ratio)

                # when current ratio is more flat
                if target_ratio < current_crop_ratio:
                    # offset : simple equation (widht / (height + offset) = 16/9)
                    offset = (9 * cropPos[0] - 16 * cropPos[1]) / 16
                    tmp_height = cropPos[1] + offset
                    tmp_height = int(tmp_height)
                    if (tmp_height % 4) != 0:
                        tmp_height -= (tmp_height % 4)
                    pad_arg = f",pad={cropPos[0]}:{tmp_height}:(ow-iw)/2:(ih-oh)/2"
                    scale_arg = f",scale=w={cropPos[0]}:h={tmp_height}"
                    print(f"[INFO]\t [PadInfo] (W : {cropPos[0]}), (H : {tmp_height})")
                else:
                    offset = (16 * cropPos[1] - 9 * cropPos[0]) / 9
                    tmp_width = cropPos[0] + offset
                    tmp_width = int(tmp_width)
                    if (tmp_width % 4) != 0:
                        tmp_width -= (tmp_width % 4)
                    pad_arg = f",pad={tmp_width}:{cropPos[1]}:(ow-iw)/2:(ih-oh)/2"
                    scale_arg = f",scale=w={tmp_width}:h={cropPos[1]}"
                    print(f"[INFO]\t [PadInfo] (W : {tmp_width}), (H : {cropPos[1]})")

            if not os.path.exists(output_dir) :
                os.mkdir(output_dir)
                print(f'[INFO]\t folder created : {output_dir}')

            output_path = os.path.join(output_dir, f"{vid_name}_box.mov")
            
            ## ffmpeg command setting
            if add_sharpening :
                sharpen_arg = ',unsharp=7:7:1.5:7:7:1.5'
            else :
                sharpen_arg = ''
            '''
            ffmpeg arguments
            -stats : print only encoding progress status (ignore loglevel argument)
            -loglevel : make ffmpeg stdout more verbose or not
                warning : only warning, error
                error : only errors
                info : defualt
            '''
            loglevel = 'error'
            ffmpeg_command = f"ffmpeg {debug_shortOutput} -i \"{fpath}\" -vf \"{crop_arg}{scale_arg}{pad_arg}{sharpen_arg}\"\
                -y -pix_fmt yuv420p -c:v libx264 -crf {crf} -c:a copy -preset medium -loglevel {loglevel}\
                {uhd_output_args} \"{output_path}\""
            print(ffmpeg_command)
            print("[INFO]\t Encoding \"%s\" ..." % vid_name)    
            print("[INFO]\t Video CRF = %d" % int(crf))

            # duration_list[0] : hour, [1] : min, [2] : sec
            duration_list = getVideDuration(fpath)
            print(f"[INFO]\t Video Duration : {duration_list[0]:02d}:{duration_list[1]:02d}:{duration_list[2]:02d}\
                Current Time : {getTime()}")
            st_time = time.time()
            
            if (logs == '') or manual_mode:
                # Manual Mode (always encoding one by one)
                # Hold process when encoding last video 
                if (vid_index + 1) == vid_num :
                    subprocess.Popen(ffmpeg_command + ' -stats', shell=False).wait()
                else :
                    subprocess.Popen(ffmpeg_command, shell=False)
            else:
                # Log file mode (encoding simultaneously n videos)
                if multi_how_many == 0:
                    p = subprocess.Popen(ffmpeg_command + ' -stats', shell=False).wait()
                    
                    # [21.12.08] progress status coding..
                    # p = subprocess.Popen(ffmpeg_command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    # while p.poll() is None:
                    #     # print('now encoding..', end='\r')
                    #     infos = p.stderr.read().decode('utf-8')
                    #     print('h',infos)
                    #     infos = p.stdout.read().decode('utf-8')
                    #     print('t',infos)
                    #     continue
                elif ((vid_index % multi_how_many == 0) and (vid_index != 0)) or ((vid_index + 1) == vid_num):
                    subprocess.Popen(ffmpeg_command + ' -stats', shell=False).wait()
                else :
                    subprocess.Popen(ffmpeg_command, shell=False)

if __name__ == "__main__":
    main()
    print("[INFO]\t Program End.")
