#!/usr/bin/env python

import sys
import re
import qt3d
import os
import fileinput
import subprocess

class Qt3DLCovCommentAdder:
    def __init__(self, rootPath):
        self.rootPath = rootPath;

    def traverse(self):
        os.chdir(self.rootPath + "/src")
        print "Traversing " + os.getcwd()
        # Traverse Qt3D source dir
        for (currentDirPath, dirNames, fileNames) in os.walk(os.getcwd()):
           for fileName in fileNames:
            # Look for all header files
               if fileName.endswith(".h") == True:
                   self.process(fileName, currentDirPath + "/" + fileName)

    def process(self, fileName, filePath):
        needsCommit = False
        foundEnum = False;
        foundDeclareMetatype = False;

        for line in fileinput.input(filePath, inplace=1):
            if line.strip().find("Q_ENUM") != -1:
                capture = list(re.findall("\s*Q_ENUM(?:S)?\((.*)\);?\n", line))
                if len(capture) == 1:
                    line = line[:-1] + " // LCOV_EXCL_LINE"
                    foundEnum = True
                    print line
                else:
                    print line[:-1]
            elif line.strip().find("Q_DECLARE_METATYPE") != -1:
                capture = list(re.findall("\s*Q_DECLARE_METATYPE\((.*)\);?\n", line))
                if len(capture) == 1:
                    line = line[:-1] + " // LCOV_EXCL_LINE"
                    foundDeclareMetatype = True
                    print line
                else:
                    print line[:-1]
            else:
                print line[:-1]

        needsCommit = foundEnum or foundDeclareMetatype
        if needsCommit == True:
            subprocess.call(["git", "add", filePath])
            print "git add " + filePath
            subprocess.call(["git", "commit", "-m " + fileName + ": add LCOV exclusion comments", "--author",  "Paul Lemire <paul.lemire350@gmail.com>"])
            print "git commit -m \"" + fileName + ": add LCOV exclusion comments\" --author Paul Lemire <paul.lemire350@gmail.com>"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage " + sys.argv[0] + "Qt3D root source directory"
        sys.exit();

    commentAdder = Qt3DLCovCommentAdder(sys.argv[1])
    commentAdder.traverse()
