#!/usr/bin/env python

import getopt
import logging
import sys
import requests
import uuid
import traceback

##################################################
# Global Variables
##################################################
debug_mode = False
url = 'https://app.harness.io/gateway/api/graphql?accountId=6dEUvjDSSMO1UDSwR60D_w'
apiKey = "NmRFVXZqRFNTTU8xVURTd1I2MERfdzo6eUtMREJBN2NTVHA1TlJ4dDFpQ2Y0S3FuN08ySHpEVThjUWlLcHN5dnpqZVk3YTYzZnl3d2JZY0JSUG5MWkZnYnBCZkZNdzlBRXhxZml0NWM="
cli_input = {
    "action": "",
    "user_name": "",
    "user_email": "",
    "user_groups": [],
    "new_group_name": "",
    "new_group_users": []
}

usage_definition = f'''
    Usage: 
    For user creation:
    python createUser_Group.py -a "create_user" -u "user_name" -e "user_email" -g "Group name 1, Group name 2, ... up to five groups"
    or 
    python createUser_Group.py --action="create_user" --user_name="user_name" --user_email="user_email" --group_names="Group name 1, Group name 2, ... up to five groups"
    
    Example:
        python ./createUser_Group.py -a create_user --user_name "avatar" -e "avatar9393734545@gmail.com" -g "Account Administrator, Avatars"
    
    -a or --action: action name, create_user for this case
    -u or --user_name: Canonical name of the user in the system, e.g. "Jonh Smith". The name can be redefined during
        user creation confirmation via e-mail link.
    -e or --user_email: existing email account for the user_name. When a user is created a new invitation email 
        is sent to the user's email account. Upon accepting invitation the user is created and added to the 
        corresponding group(s)
    -g or --group_names: Comma separated list of the canonical group(s) names which which the new user will 
        be assigned to. If one or more of the groups do not exist then the it(they) will be created and the 
        user "user_name" will be assigned to it(them).
        Examples:
            ... -g "Account Administrator"
            ... -g "Account Administrator, Avatars"
            ... --group_names "Account Administrator, Avatars"

    For group creation:
    python ./createUser_Group.py -a create_group -gg "New Group Name" --gu "Existing user 1, Existing user 2 ..."
    or 
    python ./createUser_Group.py --action create_group --new_group_name "New Group Name" --new_group_users "Existing user 1, Existing user 2 ..."
       
    Example
        python ./createUser_Group.py -a create_group --new_group_name "Avatars" --new_group_users "Vik Pik

    -a or --action: action name, create_group for this case
    -gg or --new_group_name: Canonical name of the group that will be created like "Restricted Users"
    -gu or --new_group_users: Comma separated list of the existing canonical user(s) names which will be 
        assigned to the created group
        Examples:
            ... -gu "John Smith"
            ... -gu "John Smith, Alice Bloom"
            ... --new_group_users "John Smith, Alice Bloom"
            ... --new_group_users="John Smith, Alice Bloom" 
    

    python ./createUser_Group.py -h
    or 
    python ./createUser_Group.py --help
    
        Print this help and exit

'''


########################################################
#   Parse Input Arguments
########################################################
def parse_input(argv):
    opts, args = getopt.getopt(argv, 'a: u: e: g: gg: gu: h',
                               ['help',
                                'action=',
                                'user_name=',  # for create_user flow
                                'user_email=',
                                'group_names=',  # for create_user flow
                                'new_group_name=',  # for create_group flow
                                'new_group_users='])  # for create_group flow

    if debug_mode:
        print(opts)
    # if len(opts) < 2:
    #     logging.error(usage_definition)
    #     sys.exit(2)
    # else:

    # Iterate the options and get the corresponding values
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(usage_definition)
            sys.exit(0)
        if opt in ('-a', '--action'):
            cli_input["action"] = arg
        if opt in ('-u', '--user_name'):
            cli_input["user_name"] = arg
        elif opt in ('-e', '--user_email'):
            cli_input["user_email"] = arg
        elif opt in ('-gg', '--new_group_name'):
            cli_input["new_group_name"] = arg
        elif opt in ('-gu', '--new_group_users'):
            cli_input["new_group_users"] = arg
            try:
                cli_input["new_group_users"] = [x.strip() for x in arg.split(',')]
            except Exception as err:
                logging.error(traceback.format_exc())
        elif opt in ('-g', '--group_names'):
            try:
                for group_name in [x.strip() for x in arg.split(',')]:
                    group_id = get_user_group_id(group_name)
                    if not group_id:
                        group_id = create_group(group_name)
                    cli_input["user_groups"].append(group_id)
            except Exception as err:
                logging.error(traceback.format_exc())

    # if any of the command line arguments is Null or empty (separated per flow)
    if cli_input["action"]:
        if cli_input["action"] == 'create_user':
            for val in ["user_name", "user_email", "user_groups"]:
                if not cli_input[val]:
                    logging.error(usage_definition)
                    sys.exit(2)
        elif cli_input["action"] == 'create_group':
            for val in ["new_group_name"]:
                if not cli_input[val]:
                    logging.error(usage_definition)
                    sys.exit(2)

    if debug_mode:
        print(f'''
        Arguments passed

        action:  {cli_input["action"]}
        user_name: {cli_input["user_name"]}
        user_email: {cli_input["user_email"]}
        user_groups: {cli_input["user_groups"]}
        name of the new group: {cli_input["new_group_name"]}
        users of the new group: {cli_input["new_group_users"]}
    ''')


########################################################
#   Make HTTP POST Request
########################################################
def http_request(query, variables, url):
    """
    Performs POST request to the web server
    :param query: Query to be sent to the server, string
    :param variables: Values to be substituted in the query
    :param url: URL to which the request will be sent
    :return: Response object as a dictionary
    """

    try:
        response = requests.post(url,
                                 json={'query': query, 'variables': variables},
                                 verify=False,
                                 headers={"X-Api-Key": apiKey})
        response.raise_for_status()
        # Additional code will only run if the request is successful
        response_json = response.json()
        if "errors" in response_json:
            print("Request processing failed due to an error....")
            if debug_mode:
                print(response_json)
            return response_json
        else:
            print("Request has been successfully completed....")
            if debug_mode:
                print(response_json)
            return response_json
    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)


########################################################
#   Create User and assign it to the group(s)
########################################################
def create_user(user_name, user_email, user_groups):
    """
    Creates a new user in the Harness system
    :param user_name: Canonical (usual) name of the user like "John Smith", string
    :param user_email: email account of the new user, should exist, string
    :param user_groups: list of the groups to which the new user will be assigned, list of strings
    :return: id of the new user, string
    """

    query = """mutation createUser($user: CreateUserInput!) {
      createUser(input: $user) {
        user {
          id
          email
          name
          userGroups(limit: 5) {
            nodes {
              id
              name
            }
          }
        }
        clientMutationId
  }
}
    """
    query_variables = {
        "user": {
            "name": user_name,
            "email": user_email,
            "clientMutationId": str(uuid.uuid4()),
            "userGroupIds": user_groups
        }
    }
    if debug_mode:
        print(query_variables)
        print('executing createUser API call')
    responseJson = http_request(query, query_variables, url)
    return responseJson['data']['createUser']['user']['id']


########################################################
#   Get UserID using Name
########################################################
def get_user_id_by_name(user_name):
    """
    Returns the ID of the user found by its canonical name
    :param user_name: Name of the user, e.g. "John Smith", string
    :return: ID of the user in the Harness system, string
    """

    query = """query($userName: String!){
         userByName(name:$userName){
         id }
         }
     """
    query_variables = {"userName": user_name}
    response_json = http_request(query, query_variables, url)
    user_id = None
    if not 'User does not exist' in str(response_json):
        user_id = response_json['data']['userByName']['id']
    return user_id


########################################################
#   Create Group by Name [and assign Users]
########################################################
def create_group(group_name, users_names=[]):
    """
    Creates a new group in the Harness system
    :param group_name: Name of the new group, string
    :param users_names: List of the user names that will be added to the new group, list of strings
    :return: id of the new group in the Harness system
    """

    query = """mutation($userGroup: CreateUserGroupInput!){
  createUserGroup (input:$userGroup) {
    userGroup {
      id
      name
      description
      isSSOLinked
      importedByScim
      users(limit: 190, offset: 0) {
        pageInfo {
          total
        }
        nodes {
          name
          email
        }
      }
      notificationSettings {
        sendNotificationToMembers
        sendMailToNewMembers
        slackNotificationSetting {
          slackChannelName
          slackWebhookURL
        }
        groupEmailAddresses
      }
    }
  }
}
        """
    query_variables = ''
    users_ids = []
    if users_names:
        for user_name in users_names:
            user_id = get_user_id_by_name(user_name)
            if user_id:
                users_ids.append(user_id)

        if users_ids:
            query_variables = {
                "userGroup": {
                    "name": group_name,
                    "userIds": users_ids
                }
            }
        else:
            query_variables = {
                "userGroup": {
                    "name": group_name,
                    # Uncomment this for SSO settings
                    # "ssoSetting": {"ldapSettings": {"ssoProviderId": "234234134",  "groupDN": "groupDN123",  "groupName": "fakegroup" }}
                }
            }

    else:
        query_variables = {
            "userGroup": {
                "name": group_name,
                # Uncomment this for SSO settings
                # "ssoSetting": {"ldapSettings": {"ssoProviderId": "234234134",  "groupDN": "groupDN123",  "groupName": "fakegroup" }}

            }
        }
    if debug_mode:
        print(query_variables)
    responseJson = http_request(query, query_variables, url)
    return responseJson['data']['createUserGroup']['userGroup']['id']


########################################################
#   Get UserGroupID using GroupName
########################################################
def get_user_group_id(user_group_name):
    """
    Returns ID of the Harness system group found by its canonical name, e.g. "Administrators"
    :param user_group_name: Name of the group, e.g. "Administrators", string
    :return: id of the group, string
    """

    query = """query($userGroupName: String!){
        userGroupByName(name:$userGroupName){
        id}
        }
    """

    query_variables = {"userGroupName": user_group_name}
    response_json = http_request(query, query_variables, url)
    if debug_mode:
        print(response_json)
    if 'No User Group exists' in str(response_json):
        return None
    else:
        return response_json['data']['userGroupByName']['id']


########################################################
#   Main Method
########################################################
def main():
    parse_input(sys.argv[1:])
    if cli_input["action"] == "create_user":
        create_user(user_name=cli_input["user_name"],
                    user_email=cli_input["user_email"],
                    user_groups=cli_input["user_groups"])
    elif cli_input["action"] == "create_group":
        create_group(group_name=cli_input["new_group_name"],
                     users_names=cli_input["new_group_users"])
    else:
        print("Action not allowed..")


########################################################
#   Start
########################################################
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
