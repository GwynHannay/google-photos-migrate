#!/bin/bash

echo -n "" >fixed_date_files.txt

while read -u 9 line; do
  if [ "$line" == "" ]; then
    continue
  fi

  sfile=$(echo "$line" | sed -E 's/ \| .*$//')
  gfile=$(echo "$line" | sed -E 's/.* \| //')

  date_regex='[0-9]+(:[0-9]{2}){2}\s+[0-9]{2}(:[0-9]{2}){2}'
  sdate=$(exiftool -datetimeoriginal "$sfile" | ggrep -oP "$date_regex")
  gdate=$(exiftool -datetimeoriginal "$gfile" | ggrep -oP "$date_regex")
  if [[ "$gdate" != "" && "$sdate" != "" && "$gdate" != '0000:00:00 00:00:00' && "$sdate" != '0000:00:00 00:00:00' ]]; then
    if [[ "$gdate" < "$sdate" ]]; then
      dates_file=$gfile
    elif [[ "$sdate" < "$gdate" ]]; then
      dates_file=$sfile
    else
      # Dates equal
      continue
    fi
  elif [[ "$gdate" != "" && "$gdate" != '0000:00:00 00:00:00' ]]; then
    dates_file=$gfile
  elif [[ "$sdate" != "" && "$sdate" != '0000:00:00 00:00:00' ]]; then
    dates_file=$sfile
  else
    # No nice date
    continue
  fi

  fix_file=$sfile
  if [ "$dates_file" == "$sfile" ]; then
    fix_file=$gfile
  fi

  # Copy dates to fixed
  exiftool -overwrite_original -tagsfromfile "$dates_file" -alldates '-filemodifydate<datetimeoriginal' "$fix_file" -P
  echo "$fix_file" >>fixed_date_files.txt
done 9<./duplicates_data.txt
