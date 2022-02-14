from pillar_detection_utils import *
from pillar_detection_core import *

parser = argparse.ArgumentParser()
# file path options
parser.add_argument("-i", "--input_dir", default="./input", help="Input source vid directory")
parser.add_argument("-o", "--output_dir", default="./out", help="Output vid directory")
parser.add_argument("-l", "--logfile_dir", help="Log txt file directory")

# ffmpeg encoding option
parser.add_argument("-c", "--crf", default=0, type=int, help="set crf level")  # 0: SD, 18: HD
parser.add_argument("-ivtc", "--inverse_telecine", default='fm', help="add ffmpeg telecine option [fm, bw, fmbw, False]")

parser.add_argument("-uhd", "--uhd_output", default=False, action="store_true", help="set output resolution to 3840:2160")
parser.add_argument("-fps", '-fr', "--frame_rate", default=-1, type=float, help="if minus value, same fps as input")
parser.add_argument("-lb", "--letterbox", default=False, action="store_true", help="add letterbox to make 16:9 ratio")
parser.add_argument("-sp", "--sharpening", default=False, action="store_true", help="add ffmpeg sharpening filter")


# program option
parser.add_argument("-mul", "--multi_encoding", default=1, type=int, help="when log file exist, encoding mutiple videos by this args")
parser.add_argument("-d", "--debug", default=False, action="store_true", help="for debugging. (short length video output)")

# logfile option
parser.add_argument("-s", "--cropsize_scale", default=1, type=int, help="before use crop size from logfile, scale up the crop size (for reuse when vid rescaled)")
parser.add_argument("-log", "--only_logfile", default=False, action="store_true", help="large vid mode. (only write log file.)")
parser.add_argument("-manual", "--manual_mode", default=False, action="store_true", help="manual cropping without using log file (Ignore log files)")
parser.add_argument("-edit", "--edit_mode", default=False, action="store_true", help="get first crop area from log file")

args = parser.parse_args()
# option when only write log file (no encoding) : -log
# options when only edit log file that already exists (no encoding) : -log -edit

def main():
    vid_types = ('*.avi', '*.mov', '*.mp4', '*.mxf', '*.mkv')
    manual_mode = args.manual_mode
    edit_mode = args.edit_mode
    input_dir = args.input_dir
    output_dir = args.output_dir
    
    '''
    TODO : 
    ivtc folder select
    mkdir 위치 main / core 한 쪽으로 정렬
    '''
    temp_ivtc_dir = './tmp_fm_output'

    if args.cropsize_scale < 1 :
        print(f"[!!! ERROR !!!]\t Invalid scale option [scale : {args.cropsize_scale}]")
        return
    elif args.multi_encoding < 1 :
        print(f"[!!! WARRNING !!!]\t \"multi_encoding\" option should be more then 0 [multi_encoding : {args.multi_encoding}]")
        return
    
    input_list = []
    for types in vid_types :
        input_list += glob.glob(os.path.join(input_dir, types))
    input_list = sorted(input_list)
    
    '''
    hard coding for specific file process (use "/" not "\")
    '''
#    input_dir = "Y:/Pixtree-NDA/SME/20220121_02주차/Input/중화질"
#    input_list = [
#        os.path.join(input_dir, "문희준 - Our Story (우리이야기).avi"),
#        os.path.join(input_dir, "보아 - 늘... MV_고화질.avi"),
#    ]
    
    if args.logfile_dir is not None :
        logs_dir = args.logfile_dir
    else :
        logs_dir = input_dir
    
    print("[INFO]\t Input dir :", input_dir)
    print("[INFO]\t Ouput dir :", output_dir)
    print("")
    
    for vid_index, fpath in enumerate(input_list):
        vid_name = os.path.basename(fpath)[:-4]
        vid_num = len(input_list)
        log_path = f"{logs_dir}/{vid_name}.txt"
        print(f"[INFO]\t [Video num : {vid_index + 1} / {vid_num}]")
        print("[INFO]\t File path: ", fpath)
        print("[INFO]\t Log dir :", logs_dir)

        # init crop configuration class
        crop_cfg = VideoCropCfg()
        crop_cfg.vid_name = vid_name
        crop_cfg.temp_ivtc_dir = temp_ivtc_dir
        
        # Read log file if exist
        if not manual_mode:
            cropPos, edit_mode, manual_mode = parseLog(log_path, edit_mode, manual_mode, args.cropsize_scale)

        if manual_mode or edit_mode:
            # Capture vid, Get Vid info
            crop_cfg.getVidInfo(fpath)
            
            if edit_mode:
                print("[INFO]\t (Edit mode) Read crop area from log file...")
                print(f"[INFO]\t Crop area from log file: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")
            else :
                cropPos = autoDetectCropArea(fpath)
            # Crop Area validation check (width, height must be even number)
            if cropPos == []:
                cropPos = [crop_cfg.frame_width, crop_cfg.frame_height, 0, 0]
            
            cropPos = adjustCropArea(cropPos, crop_cfg.frame_width, crop_cfg.frame_height)
            print(cropPos)

            cv2.namedWindow(f'{vid_name}', cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
            # Display crop size control UI
            while True:
                # retCode value mean
                # 0 : keep playing
                # 1 : done with cropping (to next vid)
                # 2 : replay
                # 3 : program exit
                retCode, cropPos = videoCropping(crop_cfg, cropPos)
                if retCode == 1:
                    break
                elif retCode == 2:
                    crop_cfg.getVidInfo(fpath)
                    continue
                elif retCode == 3:
                    print("")
                    return
            print("")
                    
            crop_cfg.vidRelease()
            cv2.destroyAllWindows()

            if not crop_cfg.isSkipped:
                writeLog(logs_dir, log_path, cropPos)
                
        if args.inverse_telecine != False :
            if not os.path.exists(temp_ivtc_dir):
                os.mkdir(temp_ivtc_dir)

        # Set ffmpeg commands, actual ffmpeg encoding
        if not (args.only_logfile or crop_cfg.isSkipped):
            retCode = ffmpegEncoding(args, vid_index, vid_num, cropPos, vid_name, fpath, crop_cfg)
            if retCode < 0 :
                return retCode
            
    if args.inverse_telecine != False :
        if os.path.exists(temp_ivtc_dir):
            ivtc_file_list = os.listdir(temp_ivtc_dir)
            for idx, files in enumerate(ivtc_file_list):
                file_path = os.path.join(temp_ivtc_dir, files)
                if not os.path.isdir(file_path):
                    print(f"[INFO]\t Delete temporary ivtc file : {file_path}")
                    os.remove(file_path)
            print(f"[INFO]\t Delete temporary ivtc folder : {temp_ivtc_dir}")
            os.rmdir(temp_ivtc_dir)

if __name__ == "__main__":
    main()
    print(f"\r\n Program End. end time : {getTime('string')}")
