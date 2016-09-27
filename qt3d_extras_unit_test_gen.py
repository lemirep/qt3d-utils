#!/usr/bin/env python

import sys
import re
import qt3d
import os

class UnitTestGenerator:

    def __init__(self, fileName):
        self.fileName = fileName
        self.className = ""
        self.namespace = ""
        self.properties = []

    def generateUnitTest(self):
        headerFile = open(self.fileName)
        lines = headerFile.readlines();

        hasFoundClassBeginning = False

        inCommentCount = 0

        # 1 Find the class name
        # 2 Find the Q_PROPERTIES (// READ // WRITE // NOTIFY)
        # 3 Generate test
        # Handle namespaces...

        for line in lines:
            line = line.strip()
#            print line

            if line.find('/*') == 0:
                inCommentCount += 1
                continue

            # If we are within a comment check that we are not the end
            # otherwise move to next iteration
            if inCommentCount > 0:
                if line.find('*/') != -1:
                    inCommentCount -= 1
                continue

            #early reject if comment
            if line.find('//') == 0:
                continue

            # Forward Declare
            if line.find('class') == 0 and line.find(';') != -1:
                continue

            if line.find('#') == 0:
                continue

            if line.find('class') != -1:
                classNamedict = re.findall("class\s*(?:\w+\s+)?(\w+)\s*(?:(?::)(?:\s+\w+)+(?:\s+)(?:\w+::)*\w+)?", line)
                self.className = classNamedict[0]
                continue

            # Store namespace
            if line.find('namespace') == 0:
                self.namespace = re.findall("namespace\s+(\w+)\s+{\s*", line)[0]
                print self.namespace
                continue

            if line.find('Q_PROPERTY(') == 0:
                self.properties.append(qt3d.Property(re.findall("Q_PROPERTY\(((?:\w+::)*(?:\w+)(?:(?:\s*\*\s*)|(?:\s+)))(\w+)\s+(?:(READ|WRITE|NOTIFY)\s+(\w+)\s*)(?:(READ|WRITE|NOTIFY)\s+(\w+)\s*)?(?:(READ|WRITE|NOTIFY)\s+(\w+)\s*)?(CONSTANT)?\)", line)[0]))
                continue

        headerFile.close()

    def licenseFile(self):
        lines = []
        with open('license.txt', 'r') as file:
            lines = file.readlines()
            file.close()
        return ''.join(lines)

    def generateCheckDefaultConstruction(self):
        s = "    void checkDefaultConstruction()\n"
        s += "    {\n"
        s += "        // GIVEN\n"
        s += "        " + self.namespace + "::" + self.className + " " + self.testVariableName + ";\n\n"
        s += "        // THEN\n"
        for p in self.properties:
            s += "        QCOMPARE(" + p.callGetter(self.testVariableName) + ", " + p.propertyType + ");\n"
        s += "    }\n\n"
        return s;

    def generateCheckPropertyChanges(self):
        s = "    void checkPropertyChanges()\n"
        s += "    {\n"
        s += "        // GIVEN\n"
        s += "        " + self.namespace + "::" + self.className + " " + self.testVariableName + ";\n\n"
        for p in self.properties:
            if p.hasRead == False or p.hasWrite == False or p.hasNotify == False:
                continue
            s += "        {\n"
            s += "            // WHEN\n"
            s += "            QSignalSpy spy(&" + self.testVariableName + ", SIGNAL(" + p.signal + "(" + p.propertyType + ")));\n"
            s += "            const " + p.propertyType + " newValue = // SET_VALUE_HERE;\n"
            s += "            " + p.callSetter(self.testVariableName, "newValue") + ";\n\n"
            s += "            // THEN\n"
            s += "            QCOMPARE(" + p.callGetter(self.testVariableName) + ", newValue);\n"
            s += "            QCOMPARE(spy.count(), 1);\n\n"
            s += "            // WHEN\n"
            s += "            spy.clear();\n"
            s += "            " + p.callSetter(self.testVariableName, "newValue") + ";\n\n"
            s += "            // THEN\n"
            s += "            QCOMPARE(" + p.callGetter(self.testVariableName) + ", newValue);\n"
            s += "            QCOMPARE(spy.count(), 0);\n\n"
            s += "        }\n"
        s += "    }\n\n"
        return s;


    def generateTestClass(self):
        self.testClassName = "tst_" + self.className
        self.testFileName = self.testClassName.lower() + ".cpp"
        self.testVariableName = self.className[1].lower() + self.className[2:] if self.className[0] == 'Q' else self.className[0].lower() + self.className[1:]

        s = self.licenseFile() + "\n\n"
        s += "#include <QtTest/QTest>\n"
        s += "#include <" + self.namespace + "/" + self.className.lower() + ".h>\n"
        s += "#include <QObject>\n"
        s += "#include <QSignalSpy>\n"
        s += "\n"
        s += "class " + self.testClassName + " : public QObject\n{\n"
        s += "    Q_OBJECT\n\n"
        s += "private Q_SLOTS:\n\n"
        s += self.generateCheckDefaultConstruction();
        s += self.generateCheckPropertyChanges();
        s += "};\n\n"
        s += "QTEST_APPLESS_MAIN(" + self.testClassName + ")\n\n"
        s += "#include \"" + self.testClassName.lower() + ".moc\"\n"
        return s

    def generateProFile(self):
        self.testProFileName = self.className.lower() + ".pro"
        s = "TEMPLATE = app\n\n"
        s += "TARGET = " + self.testClassName.lower() + "\n\n"
        s += "QT += 3dcore 3dcore-private 3drender 3drender-private 3dextras testlib\n\n"
        s += "CONFIG += testcase\n\n"
        s += "SOURCES += " + self.testFileName + "\n\n"
        return s

    def generate(self):
        testContent = self.generateTestClass()
        proContent = self.generateProFile()

        testDir = self.className.lower()
        if not os.path.exists(testDir):
            os.mkdir(testDir)
        os.chdir(testDir)

        print testContent
        print proContent

        with open(self.testFileName, 'w') as testFile:
            testFile.write(testContent)
        with open(self.testProFileName, 'w') as proFile:
            proFile.write(proContent)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage " + sys.argv[0] + " header file"
        sys.exit()

    generator = UnitTestGenerator(sys.argv[1])
    generator.generateUnitTest()
    print generator.generate()
