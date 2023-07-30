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

I've added a new folder (TBD) with scripts and how to use them.

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
