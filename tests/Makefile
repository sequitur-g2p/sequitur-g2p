PYTHON := python

.PHONY: 001 002 003 004
all : 001 002 003 004


G2P := $(shell find ../build/ -name g2p.py | head -n 1)
PYTHON_PATH := $(shell find ../build/ -name "_sequitur*.so"| head -n 1| sed 's/_sequitur_.*.so//g')
001:
		PYTHONPATH=$(PYTHON_PATH) $(PYTHON) $(G2P) --encoding=utf-8 --devel 5% --train  001/lexicon.txt  --write-model 001/model-1 > 001/log
		-@echo "Test 001 passed"
		-@rm 001/log  001/model-1

002:
	  -[ ! -f 002/cmudict-0.7b ] && wget -O 002/cmudict-0.7b http://svn.code.sf.net/p/cmusphinx/code/trunk/cmudict/cmudict-0.7b 
		PYTHONPATH=$(PYTHON_PATH) $(PYTHON) $(G2P) --encoding=iso-8859-1 --devel 5% --train  002/cmudict-0.7b --write-model 002/model-1 > 002/log
		-@echo "Test 002 passed"
		-@rm 002/log  002/model-1

003:
		PYTHONPATH=$(PYTHON_PATH) $(PYTHON) $(G2P) --encoding=utf-8 --devel 5% \
							 --train 003/lexicon.txt --test 003/lexicon.txt \
							 --continuous-test --self-test  --write-model 003/model-1 > 003/log
		awk '{print $$1}' 003/lexicon.txt |  PYTHONPATH=$(PYTHON_PATH) $(PYTHON) $(G2P) --encoding=utf-8 -V 0.9 --variants-number 3 --model 003/model-1 --apply - > 003/test.out
		PYTHONPATH=$(PYTHON_PATH) $(PYTHON) $(G2P) --encoding=utf-8 -V 0.9 --variants-number 3 --model 003/model-1 --word $$(tail -n 1 003/lexicon.txt | cut -f 1 -d ' ')  > 003/test_word.out
		-@echo "Test 003 passed"
		-@rm 003/log  003/model-1 003/test_word.out 003/test.out

004:
		PYTHONPATH=$(PYTHON_PATH) $(PYTHON) $(G2P) --encoding=utf-8 --devel 5% \
							 --train $@/lexicon.txt --test $@/lexicon.txt \
							 --continuous-test --self-test  --write-model $@/model-1 > $@/log
		awk '{print $$1}' $@/lexicon.txt > $@/words.txt
		cat $@/words.txt |  PYTHONPATH=$(PYTHON_PATH) $(PYTHON) $(G2P) \
			--encoding=utf-8 -V 0.9 --variants-number 3 \
			--model $@/model-1 --apply - > $@/test_1.out
		PYTHONPATH=$(PYTHON_PATH) $(PYTHON) $(G2P) \
			--encoding=utf-8 -V 0.9 --variants-number 3 \
			--model $@/model-1 --apply $@/words.txt > $@/test_2.out
		cmp $@/test_1.out $@/test_2.out
		-@rm $@/log $@/model-1 $@/test_1.out $@/test_2.out $@/words.txt
		-@echo "Test $@ passed"
