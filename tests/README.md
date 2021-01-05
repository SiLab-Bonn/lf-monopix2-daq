[![pipeline status](https://gitlab.cern.ch/silab/lf-monopix2/badges/digital/pipeline.svg)](https://gitlab.cern.ch/silab/lf-monopix2/commits/digital)
[![coverage report](https://gitlab.cern.ch/silab/lf-monopix2/badges/digital/coverage.svg)](https://gitlab.cern.ch/silab/lf-monopix2/commits/digital)




# How to install
1. install miniconda python 2.7: https://docs.conda.io/en/latest/miniconda.html
2. install required packages
    ```console
    conda install pyyaml numpy bitarray six
    conda scipy matplotlib (optional?)
    ``` 
3. clone and install cocotb 
    ```console
    $ git clone https://github.com/cocotb/cocotb
    $ cd cocotb
    $ python setup.py install
    ```
4. clone and install basil
    ```console
    $ git clone https://github.com/SiLab-Bonn/basil
    $ cd basil
    $ git checkout -b development
    $ python setup.py develop
    ```
5. clone and install lf-monopix2
    ```console
    $ git clone 
    $ cd lf-monopix2/daq
    $ python setup.py develop
    ```
# How to run
1. set environment variables
    ```console
    $ source <math-to-miniconda>/bin/activate 
    $ export PATH=${PATH}:/cadence/mentor/questa-2019.1/questasim/bin
    $ export LM_LICENSE_FILE=8000@faust02
    $ cd <path to lf-monopix2>
    ```
2. run test script
   ```console
   $ cd <path to lf-monopix2>
   $ python daq/tests/test_***.py
   ```
2.1 or run all test scripts
   ```console
   $ cd <path to lf-monopix2>
   $ ./daq/tests/run_all.sh
   ```
   log will be saved as /tmp/***.py
3. When the script fails, run clean up manually and check if the port is released.
   ```console
   $ killall make sh vish vlm tee mgls_asynch vsimk
   $ make clean
   $ rm -f Makefile
   $ netstat -an |grep 12345 
   ```
