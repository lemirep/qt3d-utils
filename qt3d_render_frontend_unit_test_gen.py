#!/usr/bin/env python

import sys
import re
import qt3d
import os

class ArrayGetter:

    def __init__(self, type, name):
        self.type = type
        self.name = name
        self.singular = name[:-1]
        self.nonPointerType = type;
        idx = self.nonPointerType.find("*")
        if idx != -1:
            self.nonPointerType = self.nonPointerType[:idx].strip();

    def getAdderName(self):
        return "add" + self.name[0].upper() + self.singular[1:]

    def getRemoverName(self):
        return "remove" + self.name[0].upper() + self.singular[1:]

    def getGetter(self):
        return self.name + "()"

class UnitTestGenerator:

    def __init__(self, fileName):
        self.fileName = fileName
        self.className = ""
        self.namespace = ""
        self.properties = []
        self.arrayGetters = []

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

            # Array getter
            arrayGetter = list(re.findall("\s*QVector<(\w+(?:\s*\*?))>\s*(\w+)\(\)\s+const;", line))
            if len(arrayGetter) == 1:
                arrayGetter = list(arrayGetter[0])
            print len(arrayGetter)
            if len(arrayGetter) == 2:
                self.arrayGetters.append(ArrayGetter(arrayGetter[0], arrayGetter[1]))

        headerFile.close()

    def licenseFile(self):
        with open('license.txt', 'r') as file:
            lines = file.readlines()
            return ''.join(lines)

    def generateCheckDefaultConstruction(self):
        s = "    void checkDefaultConstruction()\n"
        s += "    {\n"
        s += "        // GIVEN\n"
        s += "        " + self.testVariableDecl + "\n"
        s += "        // THEN\n"
        for p in self.properties:
            s += "        QCOMPARE(" + p.callGetter(self.testVariableName) + ", " + p.propertyType + ");\n"
        for a in self.arrayGetters:
            s += "        QCOMPARE(" + self.testVariableName + "." + a.getGetter() + ".size(), 0);\n"
        s += "    }\n\n"
        return s;

    def generateCheckPropertyChanges(self):
        s = "    void checkPropertyChanges()\n"
        s += "    {\n"
        s += "        // GIVEN\n"
        s += "        " + self.testVariableDecl + "\n"
        for p in self.properties:
            if p.hasRead == False or p.hasWrite == False or p.hasNotify == False:
                continue
            s += "        {\n"
            s += "            // WHEN\n"
            s += "            QSignalSpy spy(&" + self.testVariableName + ", SIGNAL(" + p.signal + "(" + p.propertyType + ")));\n"
            s += "            const " + p.propertyType + " newValue = // SET_VALUE_HERE;\n"
            s += "            " + p.callSetter(self.testVariableName, "newValue") + ";\n\n"
            s += "            // THEN\n"
            s += "            QVERIFY(spy.isValid());\n"
            s += "            QCOMPARE(" + p.callGetter(self.testVariableName) + ", newValue);\n"
            s += "            QCOMPARE(spy.count(), 1);\n\n"
            s += "            // WHEN\n"
            s += "            spy.clear();\n"
            s += "            " + p.callSetter(self.testVariableName, "newValue") + ";\n\n"
            s += "            // THEN\n"
            s += "            QCOMPARE(" + p.callGetter(self.testVariableName) + ", newValue);\n"
            s += "            QCOMPARE(spy.count(), 0);\n"
            s += "        }\n"
        for a in self.arrayGetters:
            s += "        {\n"
            s += "            // WHEN\n"
            s += "            " + a.nonPointerType + " newValue;\n"
            s += "            " + self.testVariableName + "." + a.getAdderName() + "(&newValue);\n\n"
            s += "            // THEN\n"
            s += "            QCOMPARE(" + self.testVariableName + "." + a.getGetter() + ".size(), 1);\n\n"
            s += "            // WHEN\n"
            s += "            " + self.testVariableName + "." + a.getAdderName() + "(&newValue);\n\n"
            s += "            // THEN\n"
            s += "            QCOMPARE(" + self.testVariableName + "." + a.getGetter() + ".size(), 1);\n\n"
            s += "            // WHEN\n"
            s += "            " + self.testVariableName + "." + a.getRemoverName() + "(&newValue);\n\n"
            s += "            // THEN\n"
            s += "            QCOMPARE(" + self.testVariableName + "." + a.getGetter() + ".size(), 0);\n"
            s += "        }\n"

        s += "    }\n\n"
        return s;

    def generateCheckCreationData(self):
        dataClassName = self.namespace + "::" + self.className + "Data"

        s = "    void checkCreationData()\n"
        s += "    {\n"
        s += "        // GIVEN\n"
        s += "        " + self.testVariableDecl + "\n"
        for p in self.properties:
            if p.hasRead == False or p.hasWrite == False:
                continue
            s += "        " + p.callSetter(self.testVariableName, p.propertyType) + ";\n"

        for a in self.arrayGetters:
            s += "        " + a.nonPointerType + " " + a.singular + ";\n"
            s += "        " + self.testVariableName + "." + a.getAdderName() + "(&" + a.singular + ");\n"

        for i in range(0, 2):

            s += "\n        // WHEN\n"
            if i > 0:
                s += "        " + self.testVariableName + ".setEnabled(false);\n\n"
            else:
                s += "        QVector<Qt3DCore::QNodeCreatedChangeBasePtr> creationChanges;\n\n"

            s += "        {\n"
            s += "            Qt3DCore::QNodeCreatedChangeGenerator creationChangeGenerator(&" + self.testVariableName + ");\n"
            s += "            creationChanges = creationChangeGenerator.creationChanges();\n"
            s += "        }\n\n"
            s += "        // THEN\n"
            s += "        {\n"
            s += "            QCOMPARE(creationChanges.size(), 1);\n\n"
            s += "            const auto creationChangeData = qSharedPointerCast<Qt3DCore::QNodeCreatedChange<" + dataClassName + ">>(creationChanges.first());\n"
            s += "            const " + dataClassName + " cloneData = creationChangeData->data;\n\n"
            for p in self.properties:
                if p.hasRead == False:
                    continue
                s += "            QCOMPARE(" + p.callGetter(self.testVariableName) + ", cloneData." + p.propertyName + ");\n"
            for a in self.arrayGetters:
                s += "            QCOMPARE(cloneData." + a.singular + "Ids.size(), 1);\n"
                s += "            QCOMPARE(" + a.singular + ".id(), cloneData." + a.singular + "Ids.first());\n"
            s += "            QCOMPARE(" + self.testVariableName + ".id(), creationChangeData->subjectId());\n"
            s += "            QCOMPARE(" + self.testVariableName + ".isEnabled(), " + ("true" if i == 0 else "false") + ");\n"
            s += "            QCOMPARE(" + self.testVariableName + ".isEnabled(), creationChangeData->isNodeEnabled());\n"
            s += "            QCOMPARE(" + self.testVariableName + ".metaObject(), creationChangeData->metaObject());\n"
            s += "        }\n"
        s += "    }\n\n"

        return s;

    def generateCheckBookkeeping(self):
        s = ""
        for a in self.arrayGetters:
            s += "    void check" + (a.name[0].upper() + a.singular[1:]) + "Bookkeeping()\n"
            s += "    {\n"
            s += "        // GIVEN\n"
            s += "        " + self.testVariableDecl + "\n"
            s += "        {\n"
            s += "            // WHEN\n"
            s += "            " + a.nonPointerType + " " + a.singular + ";\n";
            s += "            " + self.testVariableName + "." + a.getAdderName() + "(&" + a.singular + ");\n\n"
            s += "            QCOMPARE(" + self.testVariableName + "." + a.getGetter() + ".size(), 1);\n"
            s += "        }\n\n"
            s += "        // THEN -> should not crash\n"
            s += "        QCOMPARE(" + self.testVariableName + "." + a.getGetter() + ".size(), 0);\n"
            s += "    }\n\n"
        return s

    def generateCheckPropertyNodifications(self):
        s = ""
        for p in self.properties:
            if p.hasWrite == False:
                continue
            s += "    void check" + (p.propertyName[0].upper() + p.propertyName[1:]) + "Update()\n"
            s += "    {\n"
            s += "        // GIVEN\n"
            s += "        TestArbiter arbiter;\n"
            s += "        " + self.testVariableDecl
            s += "        arbiter.setArbiterOnNode(&" + self.testVariableName + ");\n\n"

            for i in range(0, 2):
                s += "        {\n"
                s += "            // WHEN\n"
                s += "            " + p.callSetter(self.testVariableName, p.propertyType) + ";\n"
                s += "            QCoreApplication::processEvents();\n\n"
                s += "            // THEN\n"
                if i == 0:
                    s += "            QCOMPARE(arbiter.events.size(), 1);\n"
                    s += "            auto change = arbiter.events.first().staticCast<Qt3DCore::QPropertyUpdatedChange>();\n"
                    s += "            QCOMPARE(change->propertyName(), \"" + p.propertyName + "\");\n"
                    s += "            QCOMPARE(change->value().value<" + p.propertyType + ">(), " + p.callGetter(self.testVariableName) + ");\n"
                    s += "            QCOMPARE(change->type(), Qt3DCore::PropertyUpdated);\n"
                    s += "\n            arbiter.events.clear();\n"
                else:
                    s += "            QCOMPARE(arbiter.events.size(), 0);\n"
                s += "        }\n\n"

            s += "    }\n\n"

        for a in self.arrayGetters:
            s += "    void check" + (a.name[0].upper() + a.singular[1:]) + "Update()\n"
            s += "    {\n"
            s += "        // GIVEN\n"
            s += "        TestArbiter arbiter;\n"
            s += "        " + self.testVariableDecl
            s += "        " + a.nonPointerType + " " + a.singular + ";\n";
            s += "        arbiter.setArbiterOnNode(&" + self.testVariableName + ");\n\n"
            s += "        {\n"
            s += "            // WHEN\n"
            s += "            " + self.testVariableName + "." + a.getAdderName() + "(&" + a.singular + ");\n"
            s += "            QCoreApplication::processEvents();\n\n"
            s += "            // THEN\n"
            s += "            QCOMPARE(arbiter.events.size(), 1);\n"
            s += "            auto change = arbiter.events.first().staticCast<Qt3DCore::QPropertyNodeAddedChange>();\n"
            s += "            QCOMPARE(change->propertyName(), \"" + a.singular + "\");\n"
            s += "            QCOMPARE(change->addedNodeId(), " + a.singular +".id());\n"
            s += "            QCOMPARE(change->type(), Qt3DCore::PropertyValueAdded);\n"
            s += "\n            arbiter.events.clear();\n"
            s += "        }\n\n"
            s += "        {\n"
            s += "            // WHEN\n"
            s += "            " + self.testVariableName + "." + a.getRemoverName() + "(&" + a.singular + ");\n"
            s += "            QCoreApplication::processEvents();\n\n"
            s += "            // THEN\n"
            s += "            QCOMPARE(arbiter.events.size(), 1);\n"
            s += "            auto change = arbiter.events.first().staticCast<Qt3DCore::QPropertyNodeRemovedChange>();\n"
            s += "            QCOMPARE(change->propertyName(), \"" + a.singular + "\");\n"
            s += "            QCOMPARE(change->removedNodeId(), " + a.singular +".id());\n"
            s += "            QCOMPARE(change->type(), Qt3DCore::PropertyValueRemoved);\n"
            s += "\n            arbiter.events.clear();\n"
            s += "        }\n\n"
            s += "    }\n\n"

        return s;


    def generateTestClass(self):
        self.testClassName = "tst_" + self.className
        self.testFileName = self.testClassName.lower() + ".cpp"
        self.testVariableName = self.className[1].lower() + self.className[2:] if self.className[0] == 'Q' else self.className[0].lower() + self.className[1:]
        self.testVariableDecl = self.namespace + "::" + self.className + " " + self.testVariableName + ";\n"

        s = self.licenseFile() + "\n\n"
        s += "#include <QtTest/QTest>\n"
        s += "#include <" + self.namespace + "/" + self.className.lower() + ".h>\n"
        s += "#include <" + self.namespace + "/private/" + self.className.lower() + "_p.h>\n"
        s += "#include <QObject>\n"
        s += "#include <QSignalSpy>\n"
        s += "#include <Qt3DCore/qpropertyupdatedchange.h>\n"
        if len(self.arrayGetters) > 0:
            s += "#include <Qt3DCore/qpropertynodeaddedchange.h>\n"
            s += "#include <Qt3DCore/qpropertynoderemovedchange.h>\n"

        s += "#include <Qt3DCore/private/qnodecreatedchangegenerator_p.h>\n"
        s += "#include <Qt3DCore/qnodecreatedchange.h>\n"
        s += "#include \"testpostmanarbiter.h\"\n"

        s += "\n"
        s += "class " + self.testClassName + " : public QObject\n{\n"
        s += "    Q_OBJECT\n\n"
        s += "private Q_SLOTS:\n\n"
        s += self.generateCheckDefaultConstruction()
        s += self.generateCheckPropertyChanges()
        s += self.generateCheckCreationData()
        s += self.generateCheckBookkeeping()
        s += self.generateCheckPropertyNodifications()
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
