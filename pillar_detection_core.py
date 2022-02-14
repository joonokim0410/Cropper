from pillar_detection_utils import *
import signal

class VideoCropCfg():
    def __init__(self):
        self.ffmpeg_process = []
        self.vid_name = ''
        
        self.frame_pos = 0
        self.frame_count = 0
        
        self.captured_vid = None
        self.isPaused = False
        self.isSkipped = False
        self.cleanFrame = None
        self.boxedFrame = None
        self.frame = None
        
        self.frame_width = 0
        self.frame_height = 0
        self.fps = 0
        
        self.temp_ivtc_dir = ''
        
    def getVidInfo(self, fpath):
        self.captured_vid = cv2.VideoCapture(fpath)
        self.frame_width = int(self.captured_vid.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.captured_vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.captured_vid.get(cv2.CAP_PROP_FPS)
        
    def vidRelease(self):
        self.captured_vid.release()

def videoCropping(crop_cfg, cropPos):
    '''
    retCode value mean
    0 : keep playing
    1 : done with cropping (to next vid)
    2 : replay
    3 : program exit
    '''
    retCode = 0
    
    # search_distance unit : second
    search_distance = 5
    # play_speed unit : millisecond
    play_speed = 18
    key = cv2.waitKeyEx(play_speed)

    # Close button(X button) event
    if cv2.getWindowProperty(f'{crop_cfg.vid_name}', cv2.WND_PROP_VISIBLE) < 1 :
        retCode = 3
        return retCode, []

    if key > 0 :
        # 13 == Enter key ASCII Code
        if key == 13:
            retCode = 1
        # Pause
        elif key == ord('p') or key == ord('P'):
            if crop_cfg.isPaused :
                crop_cfg.isPaused = False
            else :
                crop_cfg.isPaused = True
        # Replay
        elif key == ord('r') or key == ord('R'):
            if not crop_cfg.isPaused:
                retCode = 2
        # Move Forward
        elif key == ord('e') or key == ord('E'):
            if not crop_cfg.isPaused:
                crop_cfg.captured_vid.set(cv2.CAP_PROP_POS_FRAMES, crop_cfg.frame_pos + (crop_cfg.fps * search_distance))
        # Move Backward
        elif key == ord('q') or key == ord('Q'):
            if not crop_cfg.isPaused:
                crop_cfg.captured_vid.set(cv2.CAP_PROP_POS_FRAMES, crop_cfg.frame_pos - (crop_cfg.fps * search_distance))
        # Display key guide
        elif key == ord('h') or key == ord('H'):
            print("[INFO]\t ### KEY GUIDE ##############################################################################################################################################################")
            print("[INFO]\t #  (MOVE : wasd), (RESIZE : ijkl), (FOR / BACKWARD : q, e), (RESET : r), (PAUSE : p), (SKIP : n), (Preview : v), (Save current frame : b)(CONFIRM : enter)  #")
            print("[INFO]\t ############################################################################################################################################################################ ")
        # Skip this Vid
        elif key == ord('n') or key == ord('N'):
            print("")
            print(f"[INFO]\t Skip this video")
            crop_cfg.isSkipped = True
            retCode = 1
            return retCode, []
        # Preview this crop area on new window
        elif key == ord('v') or key == ord('V'):
            _x = cropPos[2]
            _y = cropPos[3]
            _w = cropPos[0]
            _h = cropPos[1]
            _frame = copy.deepcopy(crop_cfg.cleanFrame)
            cv2.namedWindow(f'{crop_cfg.vid_name}_current_area', cv2.WINDOW_KEEPRATIO)
            cv2.waitKey(10)
            cv2.imshow(f'{crop_cfg.vid_name}_current_area', _frame[_y: (_y + _h), _x: (_x + _w)])
        # captured_vid, download this crop area in png file
        elif key == ord('b') or key == ord('B'):
            _x = cropPos[2]
            _y = cropPos[3]
            _w = cropPos[0]
            _h = cropPos[1]
            _frame = copy.deepcopy(crop_cfg.cleanFrame)

            _vid_name = crop_cfg.vid_name.replace(" ","_")
            image_dir = "./capture_image"
            path = os.path.join(image_dir, _vid_name)
            if not os.path.exists(path) :
                os.makedirs(path)
                print(f'[INFO]\t {path} created')

            image_name = f'{_vid_name}_({crop_cfg.frame_pos}-{crop_cfg.frame_count})_before.png'
            _path = os.path.join(path, image_name)
            imwrite(_path, crop_cfg.boxedFrame)
            print(f"\n[INFO]\t Saved current frame              : {_path}")

            image_name = f'{_vid_name}_({crop_cfg.frame_pos}-{crop_cfg.frame_count})_after.png'
            _path = os.path.join(path, image_name)
            imwrite(_path, _frame[_y: (_y + _h), _x: (_x + _w)])
            print(f"[INFO]\t Saved current frame in crop area : {_path}")
        else:
            # Crop Area control
            cropPos = resizeCropInfo(key, cropPos, crop_cfg.frame_width, crop_cfg.frame_height)

    if not crop_cfg.isPaused:
        crop_cfg.frame_pos = int(crop_cfg.captured_vid.get(cv2.CAP_PROP_POS_FRAMES))
        crop_cfg.frame_count = int(crop_cfg.captured_vid.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if(crop_cfg.frame_pos >= crop_cfg.frame_count):
        retCode = 1
    else :
        # When paused, hold current frame untill unpause.
        if crop_cfg.isPaused:
            # deep copy current frame, use that frame for draw rectangle.
            crop_cfg.boxedFrame = copy.deepcopy(crop_cfg.cleanFrame)
            cv2.rectangle(crop_cfg.boxedFrame, (cropPos[2], cropPos[3]), (cropPos[2] + cropPos[0],
                    cropPos[3] + cropPos[1]), (0, 0, 255), thickness=1, lineType=cv2.LINE_8)
            cv2.imshow(f'{crop_cfg.vid_name}', crop_cfg.boxedFrame)
        else :
            _, crop_cfg.frame = crop_cfg.captured_vid.read()
            # deep copy current frame for clean preview.
            crop_cfg.cleanFrame = copy.deepcopy(crop_cfg.frame)
            cv2.rectangle(crop_cfg.frame, (cropPos[2], cropPos[3]), (cropPos[2] + cropPos[0],
                    cropPos[3] + cropPos[1]), (0, 0, 255), thickness=1, lineType=cv2.LINE_8)    
            cv2.imshow(f'{crop_cfg.vid_name}', crop_cfg.frame)
            crop_cfg.boxedFrame = copy.deepcopy(crop_cfg.frame)
        
        print("[INFO]\t Current crop area : ", end="")
        print(cropPos, end="")
        print(f"\t Frame Count ({crop_cfg.frame_pos}/{crop_cfg.frame_count})\t[PRESS \"h\" TO VIEW KEY GUIDE]", end="\r") 
    
    return retCode, cropPos

def ffmpegEncoding(args, vid_index, vid_num, cropPos, vid_name, fpath, crop_cfg):
    retCode = -1
    
    output_dir = args.output_dir
    temp_ivtc_dir = crop_cfg.temp_ivtc_dir
    
    uhd_output = args.uhd_output
    debug = args.debug
    letterbox = args.letterbox
    sharpening = args.sharpening
    manual_mode = args.manual_mode
    fps = args.frame_rate
    
    ffmpeg_process = crop_cfg.ffmpeg_process
    
    output_name_args = []
    
    debug_shortOutput = ""
    if debug :
        debug_shortOutput = "-t 15 -ss 30"
        output_name_args.append("debug")

    uhd_output_args = ""
    if uhd_output :
        uhd_output_args = "-s 3840x2160"
        output_name_args.append("uhd")

    crop_arg = f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]}"
    current_crop_ratio = cropPos[0] / cropPos[1]
    scale_arg = ""
    pad_arg = ""
    output_width, output_height = cropPos[0], cropPos[1]

    """
    Set padding(letter box) argument
    variable "offset" for 16:9 output display ratio

    pad_arg syntax:
        pad= {width after padding}:{height after padding}:{x offset of pad}:{y offset of pad}
    """
    if letterbox :
        output_name_args.append("lb")
        # Always target 16:9 display ratio
        target_ratio = 16 / 9
        # when current ratio is more flat
        if target_ratio < current_crop_ratio:
            # offset : simple equation (widht / (height + offset) = 16/9)
            offset = (9 * cropPos[0] - 16 * cropPos[1]) / 16
            tmp_height = cropPos[1] + offset
            tmp_height = int(tmp_height)
            if (tmp_height % 4) != 0:
                tmp_height -= (tmp_height % 4)
            pad_arg = f",pad={cropPos[0]}:{tmp_height}:(ow-iw)/2:(oh-ih)/2"
            scale_arg = f",scale=w={cropPos[0]}:h={tmp_height}"
            output_width, output_height = cropPos[0], tmp_height
        else:
            offset = (16 * cropPos[1] - 9 * cropPos[0]) / 9
            tmp_width = cropPos[0] + offset
            tmp_width = int(tmp_width)
            if (tmp_width % 4) != 0:
                tmp_width -= (tmp_width % 4)
            pad_arg = f",pad={tmp_width}:{cropPos[1]}:(ow-iw)/2:(oh-ih)/2"
            scale_arg = f",scale=w={tmp_width}:h={cropPos[1]}"
            output_width, output_height = tmp_width, cropPos[1]
            
    if not os.path.exists(output_dir) :
        os.mkdir(output_dir)
        # print(f'[INFO]\t folder created : {output_dir}')

    ## ffmpeg command setting
    fps_arg = ""
    sharpen_arg = ""
    crf = args.crf
    if crf >= 0 :
        output_name_args.append(f"crf{crf}")
    elif crf < 0 :
        print(f"[!!! ERROR !!!] invalid option. fps = {crf}")
        crf = 0
    if fps > 0 :
        output_name_args.append(f"fps{fps}")
        fps_arg = f"-r {fps}"
    elif fps == 0 :
        print(f"[!!! ERROR !!!] invalid option. fps = {fps}")
    if args.uhd_output :
        output_name_args.append(f"uhd")
    if args.letterbox :
        output_name_args.append(f"lb")
    if sharpening :
        sharpen_arg = ',unsharp=7:7:1.5:7:7:1.5'
        output_name_args.append("sharp")
    if args.inverse_telecine != False:
        output_name_args.append(args.inverse_telecine)
        
    if len(output_name_args) > 0 :
        output_file_name= f"{vid_name}_box({'_'.join(output_name_args)}).mov"    
    else:
        output_file_name= f"{vid_name}_box.mov"    
    output_path = os.path.join(output_dir, output_file_name)
    
    '''
    ffmpeg arguments
    -stats : print only encoding progress status (ignore loglevel argument)
    -loglevel : make ffmpeg stdout more verbose or not
        quiet   : no logs
        warning : only warning, error
        error   : only errors
        fatal   : only fatal (crash) errors
        info    : defualt
    '''
    loglevel = 'quiet'
    if args.inverse_telecine != False :
        temp_ivtc_path = f"\"{temp_ivtc_dir}/{vid_name}_crf0_fm.mov\""
        
        if args.inverse_telecine == 'fmbw':
            ffmpeg_ivtc_command = f"ffmpeg -y -i \"{fpath}\" -vf fieldmatch=mode=pc_n:combmatch=full,bwdif=0:-1:1 -c:v libx264 -crf 0 -preset ultrafast \
                                    -stats -loglevel {loglevel} {temp_ivtc_path}"
        elif args.inverse_telecine == 'bw':
            ffmpeg_ivtc_command = f"ffmpeg -y -i \"{fpath}\" -vf bwdif=0:-1:1 -c:v libx264 -crf 0 -preset ultrafast \
                                    -stats -loglevel {loglevel} {temp_ivtc_path}"
        else:
            ffmpeg_ivtc_command = f"ffmpeg -y -i \"{fpath}\" -vf fieldmatch=mode=pc_n:combmatch=full -c:v libx264 -crf 0 -preset ultrafast \
                                    -stats -loglevel {loglevel} {temp_ivtc_path}"        
        
        ffmpeg_command = f"ffmpeg {debug_shortOutput} -i {temp_ivtc_path} {fps_arg} -vf \"{crop_arg}{scale_arg}{pad_arg}{sharpen_arg}\"\
            -y -pix_fmt yuv420p -c:v libx264 -crf {crf} -c:a copy -preset medium -loglevel {loglevel} -stats\
            {uhd_output_args} \"{output_path}\""
    else :
        ffmpeg_command = f"ffmpeg {debug_shortOutput} -i \"{fpath}\" {fps_arg} -vf \"{crop_arg}{scale_arg}{pad_arg}{sharpen_arg}\"\
            -y -pix_fmt yuv420p -c:v libx264 -crf {crf} -c:a copy -preset medium -loglevel {loglevel} \
            {uhd_output_args} \"{output_path}\""
        
    vid_duration = getVideDuration(fpath)
    vid_hour = vid_duration[0]
    vid_min = vid_duration[1]
    vid_sec = vid_duration[2]
    
    print(ffmpeg_command)
    print("====================================================================")
    print("[INFO]\t Encoding Arguments")    
    print("[INFO]\t Input File          : \"%s\"" % os.path.split(fpath)[1])
    print("[INFO]\t CRF                 : %d" % int(crf))
    print("[INFO]\t Video Duration      : %02d:%02d:%02d" % (vid_hour, vid_min, vid_sec))
    print("[INFO]\t Pixel format        : YUV420p")
    print("[INFO]\t Encoding Codec      : libx264")
    print("[INFO]\t Ffmpeg Preset       : medium")
    print(f"[INFO]\t Cropping Info       : [W : {cropPos[0]} H : {cropPos[1]} X : {cropPos[2]} Y : {cropPos[3]}]")
    print("[INFO]\t Crop area ratio     : %.5f" %current_crop_ratio)
    if letterbox :
        print("[INFO]\t Target ratio        : %.5f" %target_ratio)
    if uhd_output :
        print("[INFO]\t Output Resolution   : 3840x2160")
    else:
        print("[INFO]\t Output Resolution   : %dx%d" %(output_width, output_height))
    if sharpening :
        print("[INFO]\t Sharpening arg      : %s" %sharpen_arg[1:])
    if fps > 0 :
        print("[INFO]\t Frame Rate          : %.2f" %fps)
    print("[INFO]\t Field Match apply   : %s" %args.inverse_telecine)
    print("[INFO]\t Output File Name    : %s" %output_file_name)
    print("====================================================================")
    
    vid_index += 1
    start_time = getTime()
    if manual_mode:
            # Manual Mode (always cropping one by one)
            # Hold process when encoding last video 
            if vid_index == vid_num :
                print(f"[INFO]\t Video Duration : {vid_hour:02d}:{vid_min:02d}:{vid_sec:02d}\
                    Start Time : {getTime('string')}")
                ffmpeg_process.append(subprocess.Popen(ffmpeg_command, shell=False).wait())
            else :
                ffmpeg_process.append(subprocess.Popen(ffmpeg_command, shell=False))
    else:
        # Log file mode (encoding simultaneously n videos)
        if args.multi_encoding == 0:
            if args.inverse_telecine != False:
                subprocess.Popen(ffmpeg_ivtc_command, shell=False).wait()
                subprocess.Popen(ffmpeg_command, shell=False).wait()
                
            else :
                subprocess.Popen(ffmpeg_command, shell=False).wait()
            
        elif (vid_index % args.multi_encoding == 0) or (vid_index == vid_num):
            print(f"[INFO]\t Video Duration : {vid_hour:02d}:{vid_min:02d}:{vid_sec:02d}\
                Start Time : {getTime('string')}")
            
            if args.inverse_telecine != False:
                p = subprocess.Popen(ffmpeg_ivtc_command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
                print(f"[INFO]\t Step 1. Field match...\t(File Path : {temp_ivtc_path})", end="\n")
                while p.poll() is None:
                    displayRemainTime(vid_duration, p.stderr, start_time)
                print("",end="\n")
                    
                p = subprocess.Popen(ffmpeg_command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
                print(f"[INFO]\t Step 2. Cropping...", end="\n")
                while p.poll() is None:
                    displayRemainTime(vid_duration, p.stderr, start_time)
                print("\n")
            else :
                # p = subprocess.Popen(ffmpeg_command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
                # ffmpeg_process.append(p.pid)
                # while p.poll() is None:
                #     displayRemainTime(vid_duration, p.stderr, start_time)
                # print("\n")
                
                subprocess.Popen(ffmpeg_command, shell=False).wait()
            
        else :
            if args.inverse_telecine != False:
                print(f"[INFO]\t Video Duration : {vid_hour:02d}:{vid_min:02d}:{vid_sec:02d}\
                Start Time : {getTime('string')}")
                p = subprocess.Popen(ffmpeg_ivtc_command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
                print(f"[INFO]\t Step 1. Field match...\t(File Path : {temp_ivtc_path})", end="\n")
                while p.poll() is None:
                    displayRemainTime(vid_duration, p.stderr, start_time)
                print("",end="\n")
                    
                p = subprocess.Popen(ffmpeg_command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
                print(f"[INFO]\t Step 2. Cropping...", end="\n")
                while p.poll() is None:
                    displayRemainTime(vid_duration, p.stderr, start_time)
                print("\n")
            else :
                # p = subprocess.Popen(ffmpeg_command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
                subprocess.Popen(ffmpeg_command, shell=False)
                
            # ffmpeg_process.append(p.pid)
            
        retCode = 0
        
    return retCode
    # try:
    #     if manual_mode:
    #         # Manual Mode (always cropping one by one)
    #         # Hold process when encoding last video 
    #         if vid_index == vid_num :
    #             print(f"[INFO]\t Video Duration : {vid_hour:02d}:{vid_min:02d}:{vid_sec:02d}\
    #                 Start Time : {getTime('string')}")
    #             ffmpeg_process.append(subprocess.Popen(ffmpeg_command, shell=False).wait())
    #         else :
    #             ffmpeg_process.append(subprocess.Popen(ffmpeg_command, shell=False))
    #     else:
    #         # Log file mode (encoding simultaneously n videos)
    #         if args.multi_encoding == 0:
    #             subprocess.Popen(ffmpeg_command, shell=False).wait()
                
    #         elif (vid_index % args.multi_encoding == 0) or (vid_index == vid_num):
    #             print(f"[INFO]\t Video Duration : {vid_hour:02d}:{vid_min:02d}:{vid_sec:02d}\
    #                 Start Time : {getTime('string')}")
    #             p = subprocess.Popen(ffmpeg_command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    #             ffmpeg_process.append(p.pid)
    #             while p.poll() is None:
    #                 displayRemainTime(vid_duration, p.stderr, start_time)
    #         else :
    #             p = subprocess.Popen(ffmpeg_command, shell=False)
    #             ffmpeg_process.append(p.pid)
                
    #         retCode = 0
    # except Exception as e :
    #     print('[!!! ERROR !!!]\t', e)
    #     # print(ffmpeg_process)
    #     # for p in ffmpeg_process :
    #     #     print('terminate')
    #     #     os.killpg(os.getpgid(p, signal.SIGTERM))
    #     #     # p.terminate()
    #     #     # p.kill()
                
    #     retCode = -1
    # finally :
    #     return retCode
    