import subprocess
import json
import os
import shutil
from subprocess import check_output

# Funtion runs the mediainfo command and return the folder_name to be created in the working directory for the video to be encoded
def find_mediainfo_of_file(video_filename):

    # Run mediainfo command to extract values in json format
    mediainfo_cmd = "mediainfo --output=JSON "+ video_filename
    mediainfo_output = check_output(mediainfo_cmd, shell=True)
    # Formating the json output
    mediainfo_output_decoded = mediainfo_output.decode('utf8').replace("'", '"')
    json_data = json.loads(mediainfo_output_decoded)
    mediainfo_output_string = json.dumps(json_data, indent=4, sort_keys=True)

    # Extracting the filename 
    extension_separator = '.'
    folder_name = video_filename.split(extension_separator, 1)[0]
    # Create folder for storing all the encoding files for individual video
    # checking whether folder/directory exists
    try:
        os.mkdir(folder_name)
        print("folder '{}' created ".format(folder_name))
    except FileExistsError:
        print("folder {} already exists Deleting and creating a new folder".format(folder_name))
        shutil.rmtree(folder_name)
        os.makedirs(folder_name)

    # Create a json file with media info
    with open(os.path.join(folder_name,'%s.json'%folder_name), 'w') as file:
        file.write(mediainfo_output_string) 
        file.close()
    return folder_name

# Reads the created mediainfo json file and returns the json object
def load_mediainfo_file(folder_name):
    path_to_mediainfo_json_file = '{}/{}.json'.format(folder_name,folder_name)
    try:
        with open(path_to_mediainfo_json_file) as file:
            meidainfo_data = json.load(file)
    except FileNotFoundError:
        print('{}.json File not found exiting the code'.format(folder_name))
    return meidainfo_data

# Generic funtion to find values of input keys within json object
def extract_json_data(json_object, key):
   arr = []
 
   def extract(json_object, arr, key):
       if isinstance(json_object, dict):
           for k, v in json_object.items():
               if isinstance(v, (dict, list)):
                   extract(v, arr, key)
               elif k == key:
                   arr.append(v)
       elif isinstance(json_object, list):
           for item in json_object:
               extract(item, arr, key)
       return arr
 
   values = extract(json_object, arr, key)
   return ''.join(values)

# Run ffmpeg commad to convert the input file to raw yuv format required for encoding
def convert_to_yuv_format(video_filename,folder_name):
    ffmpeg_conversion_cmd = "ffmpeg -i {} -c:v rawvideo -pixel_format yuv420p ./{}/{}.yuv".format(video_filename,folder_name,folder_name)
    try:
        if subprocess.run(ffmpeg_conversion_cmd, shell=True).returncode == 0:
            print("FFmpeg conversion susscessfull for {} ".format(folder_name))
        else:
            print ("There was an error running FFmpeg command for file {}".format(folder_name))
            raise
    except subprocess.CalledProcessError as e:
                    print(e.output)

# Perform tile encoding based on every combinations of tile confiurations, bitrates and segment duration provided in the input file
def convert_to_hevc_tile_format(folder_name):
    for configuration in tile_configurations:
            configuration_folder = '{}/{}'.format(folder_name,configuration)
            os.mkdir(configuration_folder)
            for bitrate in bitrates: 
                filename_tile_bitrate = '{}_{}_{}'.format(folder_name,configuration,bitrate) 
                kvazaar_cmd = "kvazaar -i {}/{}.yuv --input-res {}x{} --input-fps {} -o {}/{}.hvc --tiles {} --bitrate {} --slices tiles --mv-constraint frametilemargin".format(folder_name,folder_name,width,height,framerate,configuration_folder,filename_tile_bitrate,configuration,bitrate)
                try:
                    if subprocess.run(kvazaar_cmd, shell=True):
                        print("kvazaar encoding susscessfull for {} ".format(folder_name))
                    else:
                        print ("There was an error running kvazaar command for file {}".format(folder_name))
                        raise
                except subprocess.CalledProcessError as e:
                    print(e)

                # MP4Box command for packing the hevc tile video
                mp4Box_cmd = "MP4Box -add {}/{}.hvc:split_tiles -fps {} -new {}/{}.mp4".format(configuration_folder,filename_tile_bitrate,framerate,configuration_folder,filename_tile_bitrate)
                try:
                    if subprocess.run(mp4Box_cmd, shell=True):
                         print("MP4Box packing susscessfull for {} ".format(folder_name))
                    else:
                        print ("There was an error running MP4Box command for file {}".format(folder_name))
                        raise
                except subprocess.CalledProcessError as e:
                    print(e.output)

# Dashing method to convert to mpd format with multple representations
def convert_to_mpd_format(folder_name):
    for configuration in tile_configurations:
        configuration_folder = '{}/{}'.format(folder_name,configuration)
        print(configuration_folder)
        for segment in segment_durations:
            #Take all the mp4 files of the configuration with different bitrates as input for dashing command
            lstJson = [f for f in os.listdir(str(configuration_folder)) if f.endswith('.mp4')]
            all_mp4_files_of_confiuration = ' '.join(lstJson)
            all_mp4_files_of_confiuration_array = all_mp4_files_of_confiuration.split()
            path_prefix = configuration_folder + '/'
            input_files_to_dash = ' '.join([path_prefix + x for x in all_mp4_files_of_confiuration_array])
            dashing_folder = configuration_folder + '/' + segment
            try:
                os.mkdir(dashing_folder)
                print("Folder '{}' created ".format(dashing_folder))
            except FileExistsError:
                print("Folder {} already exists Deleting and creating a new folder".format(dashing_folder))
                shutil.rmtree(dashing_folder)
                os.makedirs(dashing_folder)

            mp4Box_cmd ="MP4Box -dash {} -profile live -out {}/{}_{}_{}_dash.mpd {}".format(segment,dashing_folder,folder_name,configuration,segment,input_files_to_dash)
            try:
                if subprocess.run(mp4Box_cmd, shell=True):
                    print("DASHING was susscessfull for {} ".format(folder_name))
                    print("Encoding completed for {}".format(folder_name))
                else:
                    print ("There was an error running gpac(dashing) command for file {}".format(folder_name))
                    raise
            except subprocess.CalledProcessError as e:
                print(e.output)

# Load the input json file                 
input_file = open('input.json')
input_file_data = json.load(input_file)

# Iterate over the input file
# Extract Name,Tiling Configuration, Bitrate values and Segment Duration values for each video to be encoded
for i in input_file_data['Input']:
    video_filename  = (i['Name'])
    tile_configurations = i['Configurations']
    bitrates = i['Bitrates']
    segment_durations = i['Segment_Durations']

    # Call the mediainfo function
    folder_name = find_mediainfo_of_file(video_filename )
    media_data = load_mediainfo_file(folder_name)

    # Store file extension, height and width of the video to be encoded (Required for further encoding)
    file_extenion = extract_json_data(media_data, 'FileExtension')
    height = extract_json_data(media_data, 'Height')
    width = extract_json_data(media_data, 'Width')
    framerate = extract_json_data(media_data,'FrameRate')
    try:
        convert_to_yuv_format(video_filename,folder_name)
        convert_to_hevc_tile_format(folder_name)
        convert_to_mpd_format(folder_name)
    except:
        print('Exiting the script')
        exit()
input_file.close()