Development
-----------

Translation how to

Run python setup.py extract_messages
Upload eduiddashboard/locale/eduid-dashboard.pot to transifex.com.
Translate strings in transifex.com.
Download .po file and replace the one in eduiddashboard/locale/XX/LC_MESSAGES/eduid-dashboard.po where XX is the language you translated for.
Run python setup.py update_catalog
Run python setup.py compile_catalog
