# -*- encoding: utf-8 -*-

from datetime import datetime
import dateutil.parser
import sys, os
import requests, json
from urllib3.util.retry import Retry
import magic, mimetypes
from zoneinfo import ZoneInfo

class Program():
    def __init__(self, idsVideo, getThumbnail, youtubeKey, tz, output_dirs, dateFormats):
        self.idsVideo = idsVideo
        self.getThumbnail = getThumbnail
        self.youtubeKey = youtubeKey
        self.tzinfo = ZoneInfo(tz)
        self.output_dirs = output_dirs
        self.dateFormats = dateFormats
        self.loggingfile = None
        self.resultfile = None
        self.sessionYoutube = None                
        self.sessionGoogleApis = None        
        
        self.start()
        
    def start(self):
        self.initLoggingFile()
        print("Starting program")
        self.writelog("Starting program")
        self.initSessionYoutube()        
        self.initSessionGoogleApis()
        self.initResultFile()
           
    def initLoggingFile(self):
        dateNow = self.getDateNow()
        loggingfilename = self.output_dirs['log_file'] + "videosstatslist_" + dateNow['dateFileString'] + ".log"
        try:
            self.loggingfile = open(loggingfilename, "a", encoding="utf-8")
        except Exception as e:
            print(e)
            self.exitProgram()
    
    def initResultFile(self):
        dateNow = self.getDateNow()
        resultfilename = self.output_dirs['result_file'] + "videosstatslist_" + dateNow['dateFileString'] +  ".txt"
        try:
            self.resultfile = open(resultfilename, "w", encoding="utf-8")
        except Exception as e:
            print(e)
            self.exitProgram()
    
    def getDateNow(self):
        timestamp_now = datetime.now().timestamp()
        date = datetime.fromtimestamp(timestamp_now, self.tzinfo)
        dateString = date.strftime(self.dateFormats['dateString'])
        dateDBString = date.strftime(self.dateFormats['dateDBString'])
        dateFileString = date.strftime(self.dateFormats['dateFileString'])
        
        dateNow = {"dateString": dateString, "dateDBString": dateDBString, "dateFileString": dateFileString}
        
        return dateNow

    def writelog(self, message):
        dateNow = self.getDateNow()
        self.loggingfile.write(dateNow["dateString"] + " : " + message + "\n")
        # Write in real time
        self.loggingfile.flush()
            
    def writeresult(self, message):
        self.resultfile.write(message)
        # Write in real time
        #self.resultfile.flush()
        
    def initSessionYoutube(self):
        self.sessionYoutube = self.create_session()
        
    def initSessionGoogleApis(self):
        # Youtube Data API V3 can sometimes return HTTP status 400 and 403 whereas request is valid, and sending this same request succeeds.        
        self.sessionGoogleApis = self.create_session(status_forcelist=(400, 403, 408, 425, 429, 500, 502, 503, 504))

    def create_session(
        self,
        retries=3,
        backoff_factor=1,
        backoff_jitter=0.5,
        allowed_methods=frozenset(["GET", "POST", "HEAD", "OPTIONS"]),
        status_forcelist=(408, 425, 429, 500, 502, 503, 504),
    ):

        session = requests.Session()
        
        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            backoff_jitter=backoff_jitter,
            allowed_methods=allowed_methods,
            status_forcelist=status_forcelist,
            raise_on_status=False
        )

        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def split_list(self, lst, chunk_size):
        chunks = []
        for i in range(0, len(lst), chunk_size):
            chunks.append(lst[i:i + chunk_size])
        return chunks

    # Used when errors/exceptions occured and when we want to exit right now
    def exitProgram(self):
        try:
            self.writelog("Execution had errors")
            self.writelog("Ending program")
        except Exception as e:
            print(e)

        self.clean()
        sys.exit(1)
    
    # Used at the end of program without errors/exceptions and when errors/exception occured
    def clean(self):
        try:
            # Close Files
            if self.loggingfile is not None:
                self.loggingfile.close()
            if self.resultfile is not None:    
                self.resultfile.close()
        except Exception as e:
            print("Error cleaning up : " + str(e))
    
    def main(self):
        num_videos_processed = 0
        videosList = self.idsVideo
        num_videosList = len(videosList)
        print(f"Videos : {num_videosList}")
        self.writelog(f"Videos : {num_videosList}")

        # Get additional infos of video, 50 at once to optimize quota

        # Create a new dict videosWithInfosList that will store videoId as key and youtube data api values as value
        videosWithInfosList = {}
        for v in videosList:
            videosWithInfosList[v] = {'videoId' : v}
            
        chunk_size = 50
        videosWithInfosList_chunk = self.split_list(videosList, chunk_size)

        for videos_chunk in videosWithInfosList_chunk:
            videoIdListChunk = []                
            for video in videos_chunk:
                videoIdListChunk.append(video)

            videoIdListChunkStr = ','.join(videoIdListChunk)

            # Get additional infos of videos
            additionnalInfosURL = "https://www.googleapis.com/youtube/v3/videos?key=" + self.youtubeKey + "&id=" + videoIdListChunkStr + "&part=snippet,contentDetails,liveStreamingDetails,statistics"
            print(additionnalInfosURL)
            try:
                response = self.sessionGoogleApis.get(additionnalInfosURL, timeout=(3.05, 20))
                additionnalInfosResponse = response.text
                if response.status_code == 200:
                    video_json = json.loads(additionnalInfosResponse)
                    if video_json.get('pageInfo').get('totalResults') == 0:                        
                        print(f"[×] {additionnalInfosURL} : no result")
                        self.writelog(f"[×] {additionnalInfosURL} : no result")
                        continue
                else:
                    print(f"[×] Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                    self.writelog(f"[×] Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                    self.exitProgram()
            except Exception as e:
                print(f"[×] Error additionnalInfosURL {additionnalInfosURL} : {e}")
                self.writelog(f"[×] Error additionnalInfosURL {additionnalInfosURL} : {e}")
                self.exitProgram()

            # Store video informations from Youtube Data API
            videos_additionnalInfos = video_json.get('items')
            for video_add in videos_additionnalInfos:
                videosWithInfosList[video_add.get('id')]['youtube_api'] = video_add

        # Browse every video
        for video_key, video_info in videosWithInfosList.items():
            idVideo = video_info['videoId']
            url = f"https://www.youtube.com/watch?v={idVideo}"            
            print(url)
            self.writeresult(url)
            self.writeresult("\n")
            
            if "youtube_api" not in video_info:
                print(f"[×] idVideo={idVideo} video not found")
                self.writelog(f"[×] idVideo={idVideo} video not found")
                self.writeresult("Video not found")
                self.writeresult("\n\n")
                continue

            snippet = video_info["youtube_api"].get('snippet')
            idchannel = snippet.get('channelId')
            titlechannel = snippet.get('channelTitle')
            dateVideo = snippet.get('publishedAt')
            dateVideo_object = dateutil.parser.isoparse(dateVideo)
            dateVideo_text = dateVideo_object.astimezone(self.tzinfo).strftime(self.dateFormats['dateString'])
            title = snippet.get('title')
            description = snippet.get('description')

            contentDetails = video_info["youtube_api"].get('contentDetails')
            duration = contentDetails.get('duration', '')
            durationString = duration[2:len(duration)]
            
            stats = video_info["youtube_api"].get('statistics')
            viewCount = stats.get('viewCount')
            likeCount = stats.get('likeCount')
            commentCount = stats.get('commentCount')

            print("Channel : id : " + idchannel + " title : " + titlechannel)
            self.writeresult("Channel : id : " + idchannel + " title : " + titlechannel)
            self.writeresult("\n")
            print("Date : " + dateVideo_text)
            self.writeresult("Date : " + dateVideo_text)
             
            # Get liveStreamingDetails infos
            if "liveStreamingDetails" in video_info["youtube_api"]:
                if snippet.get("liveBroadcastContent") == "none":                    
                    actualStartTime_object = dateutil.parser.isoparse(video_info["youtube_api"].get("liveStreamingDetails").get("actualStartTime", ""))
                    actualStartTime_text = actualStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                    actualEndTime_object = dateutil.parser.isoparse(video_info["youtube_api"].get("liveStreamingDetails").get("actualEndTime", ""))
                    actualEndTime_text = actualEndTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])

                    print("start : " + actualStartTime_text)
                    self.writeresult(" (start : " + actualStartTime_text)
                    print("end : " + actualEndTime_text)
                    self.writeresult(" end : " + actualEndTime_text + ")")
                elif snippet.get("liveBroadcastContent") == "live":
                    actualStartTime_object = dateutil.parser.isoparse(video_info["youtube_api"].get("liveStreamingDetails").get("actualStartTime", ""))
                    actualStartTime_text = actualStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                    actualEndTime_text = "live"
                    durationString = "None"

                    print("start : " + actualStartTime_text)
                    self.writeresult(" (start : " + actualStartTime_text)
                    print("end : " + actualEndTime_text)
                    self.writeresult(" end : " + actualEndTime_text + ")")
                elif snippet.get("liveBroadcastContent") == "upcoming":
                    actualscheduledStartTime_object = dateutil.parser.isoparse(video_info["youtube_api"].get("liveStreamingDetails").get("scheduledStartTime", ""))
                    actualscheduledStartTime_text = actualscheduledStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                    durationString = "None"

                    print("scheduled : " + actualscheduledStartTime_text)
                    self.writeresult(" (scheduled : " + actualscheduledStartTime_text + ")")

            # Get thumbnail image, cf https://developers.google.com/youtube/v3/docs/videos#snippet.thumbnails high is always there
            # "standard" and "maxres" may be present
            if self.getThumbnail is True:
                dateNow = self.getDateNow()
                thumbnails = snippet.get('thumbnails')
                thumbnail_item = thumbnails.get('high')
                if 'maxres' in thumbnails:
                    thumbnail_item = thumbnails.get('maxres')
                elif 'standard' in thumbnails:
                    thumbnail_item = thumbnails.get('standard')
                    
                thumbnail_url = thumbnail_item.get('url')
                try:
                    response = self.sessionYoutube.get(thumbnail_url, stream = True, timeout=(3.05, 20))
                    if response.status_code == 200:
                        thumbnailInfosResponse = response.content

                        # Download file without extension
                        filethumbnail = self.output_dirs['result_file'] + video_info['videoId'] + "_thumbnail_" + dateNow['dateFileString']
                        fthumbnail = open(filethumbnail, "wb")
                        fthumbnail.write(thumbnailInfosResponse)
                        fthumbnail.close()

                        # Guess mimetype, guess file extension then rename file with extension
                        fileMimetype = magic.from_file(filethumbnail, mime=True)
                        fileExtension = mimetypes.guess_extension(fileMimetype)
                        if fileExtension is not None:
                            newfilethumbnail = filethumbnail + fileExtension
                            os.rename(filethumbnail, newfilethumbnail)
                        else:
                            print(f"[×] idVideo={video_info['videoId']} filethumbnail={filethumbnail} Couldn't guess file extension mimetype={fileMimetype}, we keep file without extension")
                            self.writelog(f"[×] idVideo={video_info['videoId']} filethumbnail={filethumbnail} Couldn't guess file extension mimetype={fileMimetype}, we keep file without extension")
                    else:
                        print(f"[×] idVideo={video_info['videoId']} Response of thumbnail_url {thumbnail_url} isn't OK : {response.status_code} {response.text}")
                        self.writelog(f"[×] idVideo={video_info['videoId']} Response of thumbnail_url {thumbnail_url} isn't OK : {response.status_code} {response.text}")
                except Exception as e:
                    print(f"[×] idVideo={video_info['videoId']} Error thumbnail_url {thumbnail_url} : {e}")
                    self.writelog(f"[×] idVideo={video_info['videoId']} Error thumbnail_url {thumbnail_url} : {e}")

            self.writeresult("\n")               
            print("Title : " + str(title))
            self.writeresult("Title : " + str(title))
            self.writeresult("\n")
            print("Duration : " + str(durationString))
            self.writeresult("Duration : " + str(durationString))
            self.writeresult("\n")
            print("Description : " + str(description))
            self.writeresult("Description : " + str(description))
            self.writeresult("\n")
            print("Views : " + str(viewCount))
            self.writeresult("Views : " + str(viewCount))
            self.writeresult("\n")
            print("Likes : " + str(likeCount))
            self.writeresult("Likes : " + str(likeCount))
            self.writeresult("\n")
            print("Comments : " + str(commentCount))
            self.writeresult("Comments : " + str(commentCount))
            self.writeresult("\n")
            self.writeresult("\n")
            
            num_videos_processed = num_videos_processed + 1
            
        print(f"Processed : {num_videos_processed}")
        self.writelog(f"Processed : {num_videos_processed}")
                    
        print("Execution was OK")
        self.writelog("Execution was OK")
        print("Ending program")
        self.writelog("Ending program")
        self.clean()

if __name__ == "__main__":
    # Paths
    output_dirs = {'log_file': "",
                   'result_file': ""
    }
    # Youtube
    idsVideo = ['', '']
    getThumbnail = False
    youtubeKey = '' # YouTube API Key from Google Cloud, see https://helano.github.io/help.html

    # Format
    tz = "Europe/Paris"
    dateFormats = {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}

    # Launch
    program = Program(idsVideo, getThumbnail, youtubeKey, tz, output_dirs, dateFormats)
    program.main()

