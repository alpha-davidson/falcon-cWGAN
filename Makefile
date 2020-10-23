CXXFLAGS = -Wall
ROOTFLAGS = `$(ROOTSYS)/bin/root-config --cflags --libs`
FASTJETFLAGS = `$(FASTJETSYS)/bin/fastjet-config --cxxflags --libs --plugins`

makeHistos.out : src/partonJets.cc src/helpers.h
	$(CXX) $(CXXFLAGS) -o bin/makeHistos.out $^ $(ROOTFLAGS) $(FASTJETFLAGS)

makettbarHistos.out : src/ttbarJets.cc src/helpers.h
	$(CXX) $(CXXFLAGS) -o bin/makettbarHistos.out $^ $(ROOTFLAGS) $(FASTJETFLAGS)


makeData.out : src/makeData.cc src/helpers.h
	$(CXX) $(CXXFLAGS) -o bin/makeData.out $^ $(ROOTFLAGS) $(FASTJETFLAGS)
	
histos : 
	./bin/makeHistos.out JetNtuple_PfCands.root histos.root jetInfo.txt

ttbarHistos :
	./bin/makettbarHistos.out ttbarEvents2.root ttbarHistos.root 

data : 
	./bin/makeData.out JetNtuple_partGenMatch.root matchData.txt

clean :
	rm data/histos.root

.PHONY: data clean histos ttbarHistos
