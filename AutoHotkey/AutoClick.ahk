; A simple script to automatically click repeatedly via a toggle switch. The time in between clicks can be changed by
; setting SLEEP_TIME to appropriate value in milliseconds.

; Set MaxThreadsPerHotkey to at least 2 so that script can be disabled properly.
#MaxThreadsPerHotkey, 2

; Time to wait in between clicks (in ms).
SLEEP_TIME := 20

; As long as Active is True keep clicking.
F1::
    Active := !Active

    Loop
    {
        If (!Active)
            Break

        Click
        Sleep SLEEP_TIME
    }

Return
