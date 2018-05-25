

#!/bin/bash

date=$(date +%Y-%m-%d-%H-%M-%S)
if [ "$1" -eq 1 ] 
then
	file=$(sed '1!d' targets.txt)
	echo copying file: $file to "./google-bookmarks/Bookmarks-$date.html"
	cp "$file" "./google-bookmarks/Bookmarks-$date.html"
elif [ "$1" -eq 2 ] 
then
	#command=$(sed '2!d' targets.txt)
	#echo file name is $(sed '2!d' targets.txt)
	#file=""
	#echo $file
	file=$(find /home/sdeshpande/Downloads/ -name "*wund*" -mmin -40 | head -n 1)
	echo copying file: $file to "./wunderlist-data/wunderlist-$date"
	#echo file name is $($command)
        #cp $($(sed '2!d' targets.txt)) "./wunderlist-data/wunderlist-$date"
	cp "$file" "./wunderlist-data/wunderlist-$date"
        cp "$file" "./wunderlist-data/wunderlist-master"
elif [ "$1" -eq 3 ]
then
	dconf dump / > ./dconf.dump
else 
	echo "no line number argument provided -type 1 for google-bookmarks and 2 for wunderlist-data"
fi

#grep mediterranean -r ~/.config/
#sed '5!d' file
#awk 'NR==5' file
#echo "the $1 eats a $2 every time there is a $3"

