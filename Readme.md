0.99.3 - 2024-11-05
--------------------
* Inactive buttons and checkboxes are visually different now (you can change those colors too)
* Fixed a bug, where the checkboxes to show/hide the background plots stayed inactive,
    if the background was in the same file as the foreground
* Additional entries in About
* Changed license to CC-BY-NC-SA, as the free version of PySide6 doesn't allow commercial use.
* Removed dead entries in the config
* First Linux version released



0.99.2 - 2024-10-18:
--------------------
* You can now load background spectra and also subtract them from the loaded spectrum.
* You can also subtract backgrounds from spectrum files that already include them, or choose from file too.
* The semi-persistent setting of showing/hiding the original or compensated plot in the config.ini is changed to a permanent setting. This reduces a lot of calculations and add stability.
* Stated in the "About-box" that this program is NOT connected to, or developed by RadiaCode
* Code clean ups



0.99.1 - 2024-10-12:
--------------------
* Switched from Pyinstaller to Nuitka, as pyinstaller created false positive virus warnings,
 because of the way it works. That's why the app folder now looks differently.
* New logo instead of the temporary one(s).
* Added contact mail in the About-box for suggestions, constructive critics and bug reports.
* Links in the About-box are now clickable.
* Changed the way how negative energy values are handled.
* Removed settings for energy offset and cutoff in the config file.
* Spectra from RC101, RC102 and RC103 now get a warning if the coefficient a0 is smaller than -20.
* Spectra from RC103G now get a warning if the coefficient a0 is smaller than 0.
* Spectra from any RC device now get a warning if the coefficient a0 is greater than 30.
* This warnings will be missed or wrong, if the serial number in the XML file is empty or altered.
* Removed 2 relics from the config file.
* Removed the sound at opening of the About-box.
