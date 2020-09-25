conda create -n geminhack python=3.8 -c conda-forge -y
conda install pipenv -n geminhack -c conda-forge -y
CONDABIN=$(conda info --envs | grep geminhack | sed 's/[[:blank:]]\+/ /' | cut -d ' ' -f 2)/bin
$CONDABIN/pipenv sync --python $CONDABIN/python3.8
$CONDABIN/pipenv run python -m geminhack.ge2gi $GEMINHAACKDB
conda env remove -n geminhack
