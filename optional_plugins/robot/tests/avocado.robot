*** Settings ***
Documentation     Sleep test cases

*** Test Cases ***
NoSleep
        Sleep   0
        Log     "got no sleep"
Sleep
        Sleep   0.01
        Log     "got some sleep"
