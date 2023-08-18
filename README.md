# Google Photos Migration (google-photos-migrate)

All original work in this repository is done by Johannes Garz ([@garzj](https://github.com/garzj)), as this is forked from [their work](https://github.com/garzj/google-photos-migrate). Everything under the *src* and *android-dups* directory is untouched by me, and you can see the original instructions below.

## My Use Case

Currently, I am in the process of migrating everything I can away from Google and to self-hosting. If you want to see my thrown-together homeserver stuff, feel free to [check it out](https://github.com/GwynHannay/homeserver), but I should warn you that my priority has been to get things running so I can focus on other things and it is definitely not highly available. ;-) 

My Google Photos replacement is [Immich](https://github.com/immich-app/immich), which is under *heavy development*. Facial recognition is a recent addition and the big one I've been waiting for to get moving as it was the most important part of Google Photos for me. However, I didn't just use Google Photos to store my phone's pictures... I uploaded *everything*, and I used to take a lot of photos. The Takeout of my pictures (which I only had going up until the start of February this year) was about 86 GB, and the quality option I had selected was not the original.

Under [Further steps](#further-steps) you will see Johannes' guide on cleaning up duplicate pictures between Google Photos and the Android phone. There's scripts under [android-dups](./android-dups/) written for Linux users that will help to ensure pictures have the correct date and determine which one is of higher quality (based on image size). My original modifications were to the bash scripts to ensure they worked on MacOS, but I ended up making a lot of changes to the Python script as well to suit my use case:

- Multiple storage locations of original photos (they are all over the place on my fileserver, it's a mess)
- Original photos do not have the same name as those in Google Photos (a lot of instances where the original is '001.jpg' but at some point they'd all be renamed to things like '001 (47).jpg'
- Large volume of pictures in Google Photos alone (just over 45,000) with many more stored on my fileserver

## My Contribution

I've added a new python script (photohunter.py - that's a temporary name), modified from the original, that will (this list is out of date):

- Create a SQLite database for records of original Google Photos and the duplicates found.
- Traverse the output directory from the original google-photos-migrate scripts, storing their location, file size, created date, and the filename with the rounded braces removed.
- Iterate through a list of provided filepaths where duplicate photos may be found, find Google Photos with the same name (minus the rounded braces), compare the similarity of the two to find duplicates, then store any duplicate photo details with their location, file size, created date, and similarity score.
- Get a list of duplicate photos where the duplicate is of a larger file size than that from Google Photos, then copy them to a working directory.
- Update any dates as necessary in the duplicates, then replace the Google Photos with the better copy.

## Instructions

This is how I used everything here, from Johannes' original script through to my contributions. This is done on a MacBook with my Google Takeout files on a separate fileserver.

### Step 1: Extract Takeout Files

SSH into fileserver, navigate to the folder where I stored my 43 Google Takeout ZIP files, then:

```bash
mkdir takeout errors output copies
unzip '*.zip' -d takeout
```
> Explanation: The 'takeout' directory is where all of your Google Photos will be extracted, 'errors' is for files the original google-photos-migrate scripts can't process, 'output' is where your processed photos will end up, and 'copies' is the working directory for the duplicate photos from other locations.

### Step 2: Run Original Migration

On my local machine, where I store GitHub repos:

```bash
git clone https://github.com/GwynHannay/google-photos-migrate.git
cd google-photos-migrate

yarn
yarn build

yarn start '/path/to/fileserver/takeout' '/path/to/fileserver/output' '/path/to/fileserver/errors' --timeout 60000
```
> Explanation: All of this part is untouched by me and remains Johannes' original code, but we're cloning from my repo which includes the duplicates script. Here you will build the code created by Johannes, then run it providing the filepaths for your takeout photos, the place for the processed photos to go, and the errors directory. Make sure you have enough disk space! Also, this will take a long time, so be patient.

### Step 3: Run Duplicates Script

> **Important Note:** The above script will _copy_ your takeout photos to the new "output" location (or "errors" location if they couldn't be processed). This next section will _replace_ the photos in the "output" location, so create a backup if you're worried about how this next bit might go.

Edit the file [settings.yaml](settings.yaml) with the following:

- *timezone*: Your timezone, e.g. Australia/Perth.
- *google_location*: Filepath for your output directory from the previous step.
- *working_location*: Filepath for the working directory (the copies directory you created in step 2).
- *duplicate_locations*: List of filepaths where you have other copies of your pictures.

Create your Python virtual environment, install required packages, and run the Python script:

```bash
python3 -m venv .env
source .env/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python photohunter.py
```
> Explanation: Creating a virtual environment in Python first is good practice, so the packages we install don't mess with any other projects you might have. We also upgrade pip to the latest version as this is a good security practice, then we're installing the dependencies for the script to run. Feel free to read through the duplicates.py script to see how it all works.

# google-photos-migrate (Original Instructions)

A tool like [google-photos-exif](https://github.com/mattwilson1024/google-photos-exif), but does some extra things:

- uses the titles from the .json file to recover previous filenames
- moves duplicates into their own folder
- tries to match files by the title in their .json file
- fixes wrong extensions, identified by [ExifTool](https://exiftool.org/)
- video files won't show up as from 1970
- works for English and German (for more langs fix [this file](./src/meta/find-meta-file.ts), line 31)

## Run

```bash
git clone https://github.com/garzj/google-photos-migrate.git
cd google-photos-migrate

yarn
yarn build

mkdir output error
yarn start '/path/to/takeout/Google Fotos' './output' './error' --timeout 60000
```

## Further steps

- If you use Linux + Android, you might want to check out the scripts I used to locate duplicate media and keep the better versions in the [android-dups](./android-dups/) directory.
- Use a tool like [Immich](https://github.com/immich-app/immich) and upload your photos

## Supported extensions

Configured in [extensions.ts](./src/config/extensions.ts):

- `.jpg`
- `.jpeg`
- `.png`
- `.raw`
- `.ico`
- `.tiff`
- `.webp`
- `.heic`
- `.heif`
- `.gif`
- `.mp4`
- `.mov`
- `.qt`
- `.mov.qt`
- `.3gp`
- `.mp4v`
- `.mkv`
- `.wmv`
- `.webm`
