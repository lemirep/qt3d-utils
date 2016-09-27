import re

class Property:
    def __init__(self, propertyList):
        print propertyList
        self.propertyName = propertyList[1]
        self.propertyType = propertyList[0].strip()
        self.hasRead = False
        self.hasWrite = False;
        self.hasNotify = False;

        i = 2;
        while i < len(propertyList):
            if propertyList[i] == "READ":
                i += 1
                self.hasRead = True
                self.getter = propertyList[i]
            elif propertyList[i] == 'WRITE':
                i += 1
                self.hasWrite = True
                self.setter = propertyList[i]
            elif propertyList[i] == 'NOTIFY':
                i += 1
                self.hasNotify = True
                self.signal = propertyList[i]
            i += 1

    def getterPrototype(self):
        return self.propertyType + " " + self.getter + "() const;"

    def setterPrototype(self):
        passByCopy = (
            self.propertyType == "int" or
            self.propertyType == "float" or
            self.propertyType == "bool" or
            self.propertyType == "double"
        )
        s = "void "  + self.setter + "("
        if passByCopy == True:
            s += self.propertyType
        else:
            s += "const " + self.propertyType + "& " + self.propertyName
        s += ");"
        return s

    def getterImplementation(self, className):
        s = self.propertyType + " " + className + "::" + self.getter + "() const"
        s += "\n{\n"
        s += "return m_" + self.propertyName + ";"
        s += "\n}\n"
        return s

    def setterImplementation(self, className):
        s = self.setterPrototype()
        offset = len(self.propertyType) + 1
        s = s[:offset] + className + "::" + s[offset:len(s) - 1]
        s += "\n{\n"
        s += "    if (" + self.propertyName + " == m_" + self.propertyName + ")\n"
        s += "        return;\n"
        s += "     m_" + self.propertyName + " = " + self.propertyName + ";\n"
        if self.hasNotify:
            s += "     emit " + self.signal + "(" + self.propertyName + ");"
        s += "\n}\n"
        return s

    def callSetter(self, variable, parameter, isPointer=False):
        return variable + ("-> " if isPointer == True else ".") + self.setter + "(" + parameter + ")"

    def callGetter(self, variable, isPointer=False):
        return variable + ("-> " if isPointer == True else ".") + self.getter + "()"


    def __str__(self):
        s = "Property: " + self.propertyName + " type: " + self.propertyType
        if self.hasRead == True:
            s += " hasRead " + self.getter
        if self.hasWrite == True:
            s += " hasWrite " + self.setter
        if self.hasNotify == True:
            s += " hasNotify " + self.signal
        return s


class Member:
    def __init__(self, type, name):
        self.type = type.strip()
        self.name = name.strip()

    def callGetter(self):
        getterName = self.name
        offset = getterName.find("_")
        if offset != -1:
            getterName = getterName[offset + 1:]
        return getterName + "()"

    def callSetter(self):
        setterName = self.name
        offset = setterName.find("_")
        if offset != -1:
            setterName = setterName[offset + 1:]
        setterName = setterName[0].upper() + setterName[1:]
        return "set" + setterName + "(" + self.type  + ")"

class BackendClass:
    def __init__(self, className, namespace):
        self.className = className
        self.namespace = namespace
        self.members = []
