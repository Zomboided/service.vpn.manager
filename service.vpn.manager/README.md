VPN Manager for OpenVPN
=======================

This add-on is a combination of program add-on and service.  It allows the configuration and switching between different VPN profiles/locations.  It will reconnect to a VPN on boot and then maintain the VPN connection based on the add-ons being used.  It's primary function is to avoid having to mess with VPNs once everything is set up.

It was most definitely inspired by wanting to improve on the excellent VPN for OPENELEC from the MetalKettle repo.  Like that add-on, it also relies on the openvpn to do the dirty network stuff.


Basic Usage
-----------
To use this add-on, first set up a connection to a VPN provider and then validate with at least one profile.  The first of these is the primary VPN which will be used to reconnect at boot.  Subsequently additional connections can be set up to allow switching between them.


Add-on Filtering
----------------
Using the Add-on Filter, identify which add-ons will use which VPN and which add-ons will not use a VPN at all.  As the add-on is selected, the VPN will automatically switch to the correct profile.  When an add-on is used that doesn't have a filter, the previous VPN profile to any filtering will be reverted to.  When configuring the filters, you must restart the service (on the Settings/Monitor tab) to start using the changes.

Multiple VPNs can be selected for a single add-on.  What this means is that when you switch to an add-on, if you have a current VPN which is one of the multiple VPNs identifed then that VPN will continue to be used.  If your current VPN is not one of the multiple VPNs identified, then it'll select the lowest number VPN.

Other VPN profiles can be used via the VPN Manager for OpenELEC add-on in the Program section.


Cycling
-------
Additionally, primary VPN profiles can be cycled through either using the add-on menu, or at any time, a button on the remote.  On pressing the button the first time, the current VPN state will be displayed.  Subsequent presses will cycle around the available connections (and optionally disconnect).
After a short period (~10 seconds), the VPN last displayed will be connected.  If you don't want this to happen, cycle back to the current connected VPN.  If the network is active during a switch any traffic will likely be disrupted

To set up the cycle funtion, there's a remote.xml file within the add-on zip which shows how to map the cycle function onto a key (I'm using the blue key on my remote).  You can use the Keymap Editor add-on to create an xml file within the userdata directory (/storage/.kodi/userdata/keymaps) and edit it to contain the RunScript command show in remote.xml.


Popup Info Display
------------------
Similar to cycling, create a hot key to map to the infopopup.py module to display a system and network info window over the current screen.  Check out the cycle funtion to understand hw to add it to a remote button.


Other Function
--------------
Finally, there's a bunch of other options to turn some of the behaviour described on and off.  Everything is defaulted to sensible behaviour.


Bonus Functions
---------------
Weekly reboot and reboot based on file can be used to reboot a Kodi box.  I added this because I found that my Windows server which contained all of the media sometimes rebooted, leaving me with stale SMB handles.  Weekly reboot can be set to coincide with update/reboot cycles, or you can monitor a file which can be updated using a batch script during server boot.

Local network file speed reading tests can be performed to give you an idea of whether or not your local network is capable of sustaining the data rate required to stream media.  This was added because I tend to stream large multi GB files and was getting too many buffering issues.  There's not an internet equivalent function because there are too many factors involved (ie the target server, your provider, your internal network).


User Defined Connections and Using Two Providers
------------------------------------------------
To use the User Defined 'provider' (ie a set of connections managed by the user), put the relevant files in the userdata/addon_data/service.vpn.manager/UserDefined.  All files in this directory will be copied for use in the add-on when the first connection is attempted.  

If the User Defined settings on the Settings/VPN Configuration tab indicate that the User Defined username and password should be used, then a pass.txt file will be generated and the path to that file updated in each .ovpn file.  

Likewise if the user key and certificate option is selected, then the key and cert files will be requested during connection.  These files are put in the userdata directory and the .ovpn files updated to point to them.

Each .ovpn file can include the tag, '#PATH' which will be replaced with the working directory path.  This can be used to point at any other key/cert files which will be copied across from the userdata directory.

If any files in the User Defined userdata directory are updated, you must run the reset .ovpn files option to cause the files to be updated.

Using this function will allow a user to use two different providers at the same time.  Switch off the user/password and key and cert options.  Copy the required .ovpn files into the userdata directory, along with any keys, pass.txt files, etc for both providers.  Update the .ovpn files to use the #PATH tag to cause the files to be updated to point to the right files (or enter the actual path).  All of the files will then be copied to the right place during the first connection and will used when required.


