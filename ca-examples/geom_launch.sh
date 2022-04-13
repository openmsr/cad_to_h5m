#!/bin/bash
h5m=step_to_h5m.py
configfiles=(geom_config)
#configfiles+=(geom_config2)
#configfiles+=(geom_config3)

IFS='='
for configfile in "${configfiles[@]}"
  do
    keys=()
    values=()
    dic=()
    while read -a line
      do
        keys+=(${line[0]})
        values+=(${line[1]})
        dic+=(${line[0]}:${line[1]})
      done < $configfile
    rm *.jou *.log
    if python $h5m ${dic[@]}
      then
        mkdir "${values[0]}"
        mv *.h5m *.jou *.log ${values[0]}
        mv $configfile ${values[0]}/"geom_config"
    fi
  done
