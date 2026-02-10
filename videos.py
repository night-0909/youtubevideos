# -*- encoding: utf-8 -*-

import scrapetube
from datetime import datetime
import dateutil.parser
import sys
import requests, json
from zoneinfo import ZoneInfo

class Program():
    def __init__(self, idchannel, urlchannel, getThumbnail, youtubeKey, tz, dateFormats):
        self.idchannel = idchannel
        self.urlchannel = urlchannel
        self.getThumbnail = getThumbnail
        self.youtubeKey = youtubeKey
        self.tzinfo = ZoneInfo(tz)
        self.dateFormats = dateFormats
        
        self.initLoggingFile()
        self.initResultFile()
            
    def initLoggingFile(self):
        loggingfilename = "videosstats_" + self.idchannel
        self.loggingfile = open(loggingfilename + ".log", "a", encoding="utf-8")
    
    def initResultFile(self):
        dateNow = self.getDateNow()
        resultfilename = "videosstats_" + self.idchannel + "_" + dateNow['dateFileString'] +  ".txt"
        self.resultfile = open(resultfilename, "w", encoding="utf-8")
    
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

    def initChannel(self):
        channelInfosURL = "https://www.googleapis.com/youtube/v3/channels?key=" + self.youtubeKey + "&id=" + self.idchannel + "&part=snippet"
        print(channelInfosURL)
        try:
            response = requests.get(channelInfosURL)
            if response.status_code == 200:
                channelInfosResponse = response.text
                channel_json = json.loads(channelInfosResponse)       
                
                item = channel_json.get('items')[0]
                snippet = item.get('snippet')
                handle = snippet.get('customUrl')[1:len(snippet.get('customUrl'))]
                self.urlchannel = "https://www.youtube.com/@" + handle
            else:
                print(f"[×] channel={self.idchannel} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] channel={self.idchannel} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()
        except Exception as e:
            print(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : {e}")
            self.writelog(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : {e}")
            self.exitProgram()

    # Used when errors/exceptions occured and when we want to exit right now
    def exitProgram(self):
        self.writelog("Execution had errors")
        self.writelog("Ending program")
        self.clean()
        sys.exit(1)
    
    # Used at the end of program without errors/exceptions and when errors/exception occured
    def clean(self):
        try:
            # Close Files
            self.loggingfile.close()
            self.resultfile.close()
        except Exception as e:
            print("Error cleaning up : " + str(e))
    
    def main(self):
        print("Starting program")
        self.writelog("Starting program")
        self.initChannel()

        self.writeresult("Channel " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("\n\n")

        videostypes = ["streams", "videos", "shorts"]
        for videotype in videostypes :
            print("Type : " + videotype)
            self.writeresult("Type : " + videotype)
            self.writeresult("\n\n")
            videos = scrapetube.get_channel(channel_id=self.idchannel, content_type=videotype, sort_by="newest")
            for video in videos:
                url = "https://www.youtube.com/watch?v="+str(video['videoId'])
                print(url)
                self.writeresult(url)
                self.writeresult("\n")
                
                additionnalInfosURL = "https://www.googleapis.com/youtube/v3/videos?key=" + self.youtubeKey + "&id=" + video['videoId'] + "&part=snippet,contentDetails,liveStreamingDetails,statistics"
                print(additionnalInfosURL)
                try:
                    response = requests.get(additionnalInfosURL)
                    if response.status_code == 200:
                        additionnalInfosResponse = response.text
                        video_json = json.loads(additionnalInfosResponse)
                    else:
                        print(f"[×] idVideo={video['videoId']} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                        self.writelog(f"[×] idVideo={video['videoId']} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                        self.exitProgram()
                except Exception as e:
                    print(f"[×] idVideo={video['videoId']} Error additionnalInfosURL {additionnalInfosURL} : {e}")
                    self.writelog(f"[×] idVideo={video['videoId']} Error additionnalInfosURL {additionnalInfosURL} : {e}")
                    self.exitProgram()
                
                item = video_json.get('items')[0]
                snippet = item.get('snippet')
                dateVideo = snippet.get('publishedAt')
                dateVideo_object = dateutil.parser.isoparse(dateVideo)
                dateVideo_text = dateVideo_object.astimezone(self.tzinfo).strftime(self.dateFormats['dateString'])
                title = snippet.get('title')
                description = snippet.get('description')

                contentDetails = item.get('contentDetails')
                duration = contentDetails.get('duration')
                durationString = duration[2:len(duration)]
                
                stats = item.get('statistics')
                viewCount = stats.get('viewCount')
                likeCount = stats.get('likeCount')
                commentCount = stats.get('commentCount')

                print("Date : " + dateVideo_text)
                self.writeresult("Date : " + dateVideo_text)

                if "liveStreamingDetails" in item:
                    actualStartTime_object = dateutil.parser.isoparse(item.get("liveStreamingDetails").get("actualStartTime", ""))
                    actualStartTime_text = actualStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats['dateString'])
                    actualEndTime_object = dateutil.parser.isoparse(item.get("liveStreamingDetails").get("actualEndTime", ""))
                    actualEndTime_text = actualEndTime_object.astimezone(self.tzinfo).strftime(self.dateFormats['dateString'])
                    print("start : " + actualStartTime_text)
                    self.writeresult(" (start : " + actualStartTime_text)
                    print("end : " + actualEndTime_text)
                    self.writeresult(" end : " + actualEndTime_text + ")")

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
                        response = requests.get(thumbnail_url, stream = True)
                        if response.status_code == 200:
                            thumbnailInfosResponse = response.content
                            filethumbnail = video['videoId'] + "_thumbnail_" + dateNow['dateFileString'] + ".jpeg"
                            fthumbnail = open(filethumbnail, "wb")
                            fthumbnail.write(thumbnailInfosResponse)
                            fthumbnail.close()
                        else:
                            print(f"[×] idVideo={video['videoId']} Response of thumbnail_url {thumbnail_url} isn't OK : {response.status_code} {response.text}")
                            self.writelog(f"[×] idVideo={video['videoId']} Response of thumbnail_url {thumbnail_url} isn't OK : {response.status_code} {response.text}")
                            self.exitProgram()
                    except Exception as e:
                        print(f"[×] idVideo={video['videoId']} Error thumbnail_url {thumbnail_url} : {e}")
                        self.writelog(f"[×] idVideo={video['videoId']} Error thumbnail_url {thumbnail_url} : {e}")
                        self.exitProgram()

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
                    
        print("Execution was OK")
        self.writelog("Execution was OK")
        print("Ending program")
        self.writelog("Ending program")
        self.clean()

if __name__ == "__main__":
    # Youtube
    urlchannel = "https://www.youtube.com/@your_channel"
    idchannel = '' # Found channel id on Youtube by clicking "Share channel" then "Copy channel ID"
    getThumbnail = False
    youtubeKey = '' # YouTube API Key from Google Cloud, see https://helano.github.io/help.html

    # Format
    tz = "Europe/Paris"
    dateFormats = {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}

    # Launch
    program = Program(idchannel, urlchannel, getThumbnail, youtubeKey, tz, dateFormats)
    program.main()
