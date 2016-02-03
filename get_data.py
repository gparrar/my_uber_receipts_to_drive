#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
import httplib2
import os
import re
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
import base64
import email
from apiclient import errors
import json



try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://mail.google.com/'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'My Uber receipts'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'client_secret.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def ListUnreadUberMesaages(service, user_id, label_ids=[],query=''):
  """List all Messages of the user's mailbox with label_ids applied.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    label_ids: Only return Messages with these labelIds applied.

  Returns:
    List of Messages that have all required Labels applied. Note that the
    returned list contains Message IDs, you must use get with the
    appropriate id to get the details of a Message.
  """
  try:
      response = service.users().messages().list(userId=user_id,labelIds=label_ids,q=query).execute()
      messages = []
      if 'messages' in response:
          messages.extend(response['messages'])
      while 'nextPageToken' in response:
          page_token = response['nextPageToken']
          response = service.users().messages().list(userId=user_id,labelIds=label_ids,q=query,pageToken=page_token).execute()
          messages.extend(response['messages'])
      return messages
  except errors.HttpError, error:
      print('An error occurred: %s' % error)

def ListLabels(service, user_id):
  """Get a list all labels in the user's mailbox.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.

  Returns:
    A list all Labels in the user's mailbox.
  """
  try:
    response = service.users().labels().list(userId=user_id).execute()
    labels = response['labels']
    for label in labels:
      print('Label id: %s - Label name: %s' % (label['id'], label['name']))
    return labels
  except errors.HttpError, error:
    print ('An error occurred: %s' % error)

def GetMimeMessage(service, user_id, msg_id):
  """Get a Message and use it to create a MIME Message.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    msg_id: The ID of the Message required.

  Returns:
    A MIME Message, consisting of data from Message.
  """
  try:
    message = service.users().messages().get(userId=user_id, id=msg_id,
                                             format='raw').execute()

    print('Message snippet: %s' % message['snippet'])

    msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))

    mime_msg = email.message_from_string(msg_str)

    return mime_msg
  except errors.HttpError, error:
    print('An error occurred: %s' % error)

"""Modify an existing Message's Labels.
"""

from apiclient import errors


def ModifyMessage(service, user_id, msg_id, msg_labels):
  """Modify the Labels on the given Message.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    msg_id: The id of the message required.
    msg_labels: The change in labels.

  Returns:
    Modified message, containing updated labelIds, id and threadId.
  """
  try:
    message = service.users().messages().modify(userId=user_id, id=msg_id,
                                                body=msg_labels).execute()

    label_ids = message['labelIds']

    print('Message ID: %s - With Label IDs %s' % (msg_id, label_ids))
    return message
  except errors.HttpError, error:
    print('An error occurred: %s' % error)


def CreateMsgLabels(add,remove):
  """Create object to update labels.
  Args:
    add: List of labels to add
    remove: List of labels to remove


  Returns:
    A label update object.
  """
  return {'removeLabelIds': remove, 'addLabelIds': add}


credentials = get_credentials()
http = credentials.authorize(httplib2.Http())
service = discovery.build('gmail', 'v1', http=http)

ListLabels(service,'me')
#print(ListUnreadUberMesaages(service,'me',label_ids=['UNREAD'],query='from:receipts.london@uber.com'))
#print(ListMessagesWithLabels(service,'me',label_ids=['UNREAD']))
messages = ListUnreadUberMesaages(service,'me',label_ids=['UNREAD'],query='from:receipts.london@uber.com')

# Get Information about the ride or rides
info_list = []
for message in messages:
    info = {}
    id = message['id']
    for part in GetMimeMessage(service,'me',id).walk():
        if part.get_content_type() == "text/plain":
            body = part.get_payload(decode=True)
            #print(body)
            total = re.search('Total: £([0-9]*\.[0-9]*)',body)
            date = re.search('\d+\s[A-Z][a-z]*\s\d+',body)
            info['total'] = total.group(1)
            info['date'] = date.group()
            info_list.append(info)
    ModifyMessage(service,'me',id,CreateMsgLabels(['Label_49'],['UNREAD']))

def export_json(name,data):
    with open(name, 'w') as outfile:
        json.dump(data, outfile)

# export json to publish to Google Sheets
export_json('uber_receipts.json',info_list)