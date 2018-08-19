# -*- coding: utf-8 -*-

from .helpermenus import MessageMenu, Menu


class FAQMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Frequently Asked Questions')
        self.items = [MessageMenu('What is the meaning with this program?',
                                  '''
            We want to avoid keeping lots of cash in PVVVV\'s money box and to
            make it easy to pay for stuff without using money.  (Without using
            money each time, that is.  You do of course have to pay for the things
            you buy eventually).

            Dibbler stores a "credit" amount for each user.  When you register a
            purchase in Dibbler, this amount is decreased.  To increase your
            credit, add money to the money box and use "Adjust credit" to tell
            Dibbler about it.
            '''),
                      MessageMenu('Can I still pay for stuff using cash?',
                                  'Yes.  You can safely ignore this program completely.'),
                      MessageMenu('How do I exit from a submenu/dialog/thing?',
                                  'Type "exit" or C-d.'),
                      MessageMenu('What does "." mean?',
                                  '''
            The "." character, known as "full stop" or "period", is most often
            used to indicate the end of a sentence.

            It is also used by Dibbler to indicate that the program wants you to
            read some text before continuing.  Whenever some output ends with a
            line containing only a period, you should read the lines above and
            then press enter to continue.
                                  '''),
                      MessageMenu('Why is the user interface so terribly unintuitive?',
                                  '''
            Answer #1:  It is not.

            Answer #2:  We are trying to compete with PVV\'s microwave oven in
            userfriendliness.

            Answer #3:  YOU are unintuitive.
            '''),
                      MessageMenu('Why is there no help command?',
                                  'There is.  Have you tried typing "help"?'),
                      MessageMenu('Where are the easter eggs?  I tried saying "moo", but nothing happened.',
                                  'Don\'t say "moo".'),
                      MessageMenu('Why does the program speak English when all the users are Norwegians?',
                                  'Godt spørsmål.  Det virket sikkert som en god idé der og da.'),
                      MessageMenu('I found a bug; is there a reward?',
                                  '''
            No.

            But if you are certain that it is a bug, not a feature, then you
            should fix it (or better: force someone else to do it).

            Follow this procedure:

            1. Check out the Dibbler code from https://dev.pvv.ntnu.no/svn/dibbler

            2. Fix the bug.

            3. Check that the program still runs (and, preferably, that the bug is
               in fact fixed).

            4. Commit.

            5. Update the running copy from svn:

                $ su -
                # su -l -s /bin/bash pvvvv
                $ cd dibbler
                $ svn up

            6. Type "restart" in Dibbler to replace the running process by a new
               one using the updated files.
            '''),
                      MessageMenu('My question isn\'t listed here; what do I do?',
                                  '''
            DON\'T PANIC.

            Follow this procedure:

            1. Ask someone (or read the source code) and get an answer.

            2. Check out the Dibbler code from https://dev.pvv.ntnu.no/svn/dibbler

            3. Add your question (with answer) to the FAQ and commit.

            4. Update the running copy from svn:

                $ su -
                # su -l -s /bin/bash pvvvv
                $ cd dibbler
                $ svn up

            5. Type "restart" in Dibbler to replace the running process by a new
               one using the updated files.
            ''')]
