# flickr-uploader
Simple script to upload a folder of photos/videos to a new set in Flickr. I use it from a Raspberry Pi, to upload the photos to flickr.

Based in the work of https://github.com/alfem/synology-flickr-folder-uploader, https://github.com/sybrenstuvel/flickrapi and https://github.com/jamesmstone
/flickr-uploadr

## Installation
* sudo apt-get install python-flickrapi
* Create a new app in your Flickr account: https://www.flickr.com/services/apps/create/apply and jot down api_key and api_secret
* Edit the script and adjust the api_key, api_secreet and paths at the begining
* Run it!

  ./flickr-uploader.py -n album_name -f image.jpg

* On first run, the script will show an URL you need to visit in order to authorize it.Open the url in your brwoser, authorize the script and copy the code shown.   

You can install the api system wide and avoid setting the PYTHONPATH, but I prefer to keep my NAS system clean.

