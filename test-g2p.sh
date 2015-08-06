#!/bin/bash
#$ -S /bin/bash
#$ -m e
#$ -N g2p-test
#$ -l arch=glinux
#$ -l mem_free=1G
#$ -cwd
. ~/.environment

set -e

bin=tmp-test-install/bin
export PYTHONPATH=tmp-test-install/lib/python2.4/site-packages

g2p=./g2p.py

series=test-g2p
target=tmp-test-result
train=~/sr/g2p/databases/celex-en/train-10000-sample.lex

train=$(tempfile)
head -5000 ~/sr/g2p/databases/celex-en/train-10000-sample.lex >$train
test=$(tempfile)
tail -100 ~/sr/g2p/databases/celex-en/train-10000-sample.lex >$test

mkdir -p $target
cp $0 $target

for M in 1 2 3 4 5 ; do
  if [ $M -gt 1 ]; then
    init="
    --model	$target/$series-M$[$M-1].pic
    --ramp-up		"
  else
    init=""
  fi

#  mpatrol \
#  --dynamic \
#  --prof \
#  --prof-file $target/mpatrol-M$M.mprof \
  python $g2p $init \
  --train	$train				\
  --checkpoint					\
  --devel	5%				\
  --test        $test                           \
  --continuous-test                             \
  --write-model $target/$series-M$M.pic		\
  --self-test					\
  > $target/$series-M$M-train.log

# --size-constraints 0,4,0,4			\
#  --profile	$series-M$M-train.profile	\

#  $g2p \
#  --model	$series-M$M.pic			\
#  --test	$test                          	\
#  --profile	$series-M$M-test.profile	\
#  --result      $series-M$M-test.tab            \
#  > $series-M$M-test.log
done
