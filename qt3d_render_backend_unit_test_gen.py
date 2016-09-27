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
        self.classes = []

    def generateUnitTest(self):
        headerFile = open(self.fileName)
        lines = headerFile.readlines();

        hasFoundClassBeginning = False

        inCommentCount = 0
        namespaceCount = 0;
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
                print "Class " + self.className
                self.classes.append(qt3d.BackendClass(self.className, self.namespace))
                continue

            if len(re.findall("^}(?:\s*//.*)?$", line)) > 0:
                print "Ending namepsace " + self.namespace
                if namespaceCount > 1:
                    self.namespace = self.namespace[:self.namespace.rfind("::")]
                else:
                    self.namespace = ""
                print "-> " + self.namespace
                namespaceCount -= 1

            # Store namespace
            if line.find('namespace') == 0:
                namespace = re.findall("namespace\s+(\w+)\s+{\s*", line)[0]

                if namespaceCount > 0:
                    self.namespace += "::" + namespace
                else:
                    self.namespace = namespace

                namespaceCount += 1
                print "namespace " + self.namespace
                continue

            self.variables = list(re.findall("^((?:\w+::)*\w+(?:<(?:\w+::)*\w+\s*\**>)*\**(?:\s+)\**)((?:\w|\d)+);", line))
            if len(self.variables) > 0:
                self.variables = list(self.variables[0])
                self.classes[-1].members.append(qt3d.Member(self.variables[0], self.variables[1]))
                print self.classes[-1].members

            headerFile.close()

    def licenseFile(self):
        with open('license.txt', 'r') as file:
            lines = file.readlines()
            return ''.join(lines)

    def generateCheckInitialState(self):
        s = "    void checkInitialState()\n"
        s += "    {\n"
        s += "        // GIVEN\n"
        s += "        " + self.testVariableDecl + "\n"
        s += "        // THEN\n"
        s += "        QCOMPARE(" + self.testVariableName + ".isEnabled(), false);\n"
        s += "        QVERIFY(" + self.testVariableName + ".peerId().isNull());\n"
        for m in self.classes[0].members:
            if m.type.find("ector<") == -1:
                s += "        QCOMPARE(" + self.testVariableName + "." + m.callGetter() + ", " + m.type + ");\n"
            else:
                s += "        QVERIFY(" + self.testVariableName + "." + m.callGetter() + ".empty());\n"
        s += "    }\n\n"
        return s

    def generateCheckCleanup(self):
        s = "    void checkCleanupState()\n"
        s += "    {\n"
        s += "        // GIVEN\n"
        s += "        " + self.testVariableDecl + "\n"
        s += "        // WHEN\n"
        s += "        " + self.testVariableName + ".setEnabled(true);\n"
        for m in self.classes[0].members:
            s += "        " + self.testVariableName + "." + m.callSetter() + ";\n"
        s += "\n        " + self.testVariableName + ".cleanup();\n\n"
        s += "        // THEN\n"
        s += "        QCOMPARE(" + self.testVariableName + ".isEnabled(), false);\n"
        for m in self.classes[0].members:
            if m.type.find("ector<") == -1:
                s += "        QCOMPARE(" + self.testVariableName + "." + m.callGetter() + ", " + m.type + ");\n"
            else:
                s += "        QCOMPARE(" + self.testVariableName + "." + m.callGetter() + ".size(), int );\n"
        s += "    }\n\n"
        return s

    def generateCheckInitializeFromPeer(self):
        s = "    void checkInitializeFromPeer()\n"
        s += "    {\n"
        s += "        // GIVEN\n"
        frontendClassType = self.namespace.split("::")[0] + "::Q" + self.className
        frontendName = self.className[0].lower() + self.className[1:]
        s += "        " + frontendClassType + " " + frontendName + ";\n\n";

        s += "        {\n"
        s += "            // WHEN\n"
        s += "            " + self.testVariableDecl
        s += "            simulateInitialization(&" + frontendName + ", &" + self.testVariableName + ");\n\n"

        s += "            // THEN\n"
        s += "            QCOMPARE(" + self.testVariableName + ".isEnabled(), true);\n"
        s += "            QCOMPARE(" + self.testVariableName + ".peerId(), " + frontendName + ".id());\n"
        for m in self.classes[0].members:
            s += "            QCOMPARE(" + self.testVariableName + "." + m.callGetter() + ", " + m.type + ");\n"
        s += "        }\n"

        s += "        {\n"
        s += "            // WHEN\n"
        s += "            " + self.testVariableDecl
        s += "            " + frontendName + ".setEnabled(false);\n"
        s += "            simulateInitialization(&" + frontendName + ", &" + self.testVariableName + ");\n\n"

        s += "            // THEN\n"
        s += "            QCOMPARE(" + self.testVariableName + ".peerId(), " + frontendName + ".id());\n"
        s += "            QCOMPARE(" + self.testVariableName + ".isEnabled(), false);\n"
        s += "        }\n"

        s += "    }\n\n"
        return s

    def generateCheckSceneChangeEvent(self):
        s = "    void checkSceneChangeEvents()\n"
        s += "    {\n"
        s += "        // GIVEN\n"
        s += "        " + self.testVariableDecl
        s += "        TestRenderer renderer;\n"
        s += "        " + self.testVariableName + ".setRenderer(&renderer);\n\n"
        s += "        {\n"
        s += "             // WHEN\n"
        s += "             const bool newValue = false;\n"
        s += "             const auto change = Qt3DCore::QPropertyUpdatedChangePtr::create(Qt3DCore::QNodeId());\n"
        s += "             change->setPropertyName(\"enabled\");\n"
        s += "             change->setValue(newValue);\n"
        s += "             " + self.testVariableName + ".sceneChangeEvent(change);\n\n"
        s += "             // THEN\n"
        s += "            QCOMPARE(" + self.testVariableName + ".isEnabled(), newValue);\n"
        s += "        }\n"

        for m in self.classes[0].members:
            s += "        {\n"
            s += "             // WHEN\n"
            s += "             const " + m.type + " newValue = " + m.type + ";\n"
            s += "             const auto change = Qt3DCore::QPropertyUpdatedChangePtr::create(Qt3DCore::QNodeId());\n"
            s += "             change->setPropertyName(\"" + m.callGetter()[:-2] + "\");\n"
            s += "             change->setValue(QVariant::fromValue(newValue));\n"
            s += "             " + self.testVariableName + ".sceneChangeEvent(change);\n\n"
            s += "             // THEN\n"
            s += "            QCOMPARE(" + self.testVariableName + "." + m.callGetter() + ", newValue);\n"
            s += "        }\n"

        s += "    }\n\n"
        return s;

    def generateTestClass(self):
        self.testClassName = "tst_" + self.className
        self.testFileName = self.testClassName.lower() + ".cpp"
        self.testVariableName = "backend" + self.className
        self.testVariableDecl = self.namespace + "::" + self.className + " " + self.testVariableName + ";\n"

        s = self.licenseFile() + "\n\n"
        s += "#include <QtTest/QTest>\n"
        s += "#include <" + self.namespace.split("::")[0] + "/q" + self.className.lower() + ".h>\n"
        s += "#include <" + self.namespace.split("::")[0] + "/private/q" + self.className.lower() + "_p.h>\n"
        s += "#include <" + self.namespace.split("::")[0] + "/private/" + self.className.lower() + "_p.h>\n"
        s += "#include <Qt3DCore/qpropertyupdatedchange.h>\n"
        s += "#include \"qbackendnodetester.h\"\n"
        s += "#include \"testrenderer.h\"\n"
        s += "\n"
        s += "class " + self.testClassName + " : public Qt3DCore::QBackendNodeTester\n{\n"
        s += "    Q_OBJECT\n\n"
        s += "private Q_SLOTS:\n\n"
        s += self.generateCheckInitialState()
        s += self.generateCheckCleanup()
        s += self.generateCheckInitializeFromPeer()
        s += self.generateCheckSceneChangeEvent()
        s += "};\n\n"
        s += "QTEST_MAIN(" + self.testClassName + ")\n\n"
        s += "#include \"" + self.testClassName.lower() + ".moc\"\n"
        return s

    def generateProFile(self):
        self.testProFileName = self.className.lower() + ".pro"
        s = "TEMPLATE = app\n\n"
        s += "TARGET = " + self.testClassName.lower() + "\n\n"
        s += "QT += 3dcore 3dcore-private 3drender 3drender-private testlib\n\n"
        s += "CONFIG += testcase\n\n"
        s += "SOURCES += " + self.testFileName + "\n\n"
        s += "include(../../core/common/common.pri)\n"
        s += "include(../commons/commons.pri)\n"
        return s

    def generate(self):
        self.className = self.classes[0].className
        self.namespace = self.classes[0].namespace

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
