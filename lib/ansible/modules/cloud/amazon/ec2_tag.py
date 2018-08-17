#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['stableinterface'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
---
module: ec2_tag
short_description: create and remove tags on ec2 resources.
description:
    - Creates, removes and lists tags for any EC2 resource.  The resource is referenced by its resource id (e.g. an instance being i-XXXXXXX).
      It is designed to be used with complex args (tags), see the examples.
version_added: "1.3"
requirements: [ "boto3", "botocore" ]
options:
  resource:
    description:
      - The EC2 resource id.
    required: true
  state:
    description:
      - Whether the tags should be present or absent on the resource. Use list to interrogate the tags of an instance.
    default: present
    choices: ['present', 'absent', 'list']
  tags:
    description:
      - a hash/dictionary of tags to add to the resource; '{"key":"value"}' and '{"key":"value","key":"value"}'
    required: true
  purge_tags:
    description:
      - Whether unspecified tags should be removed from the resource.
      - "Note that when combined with C(state: absent), specified tags with non-matching values are not purged."
    type: bool
    default: no
    version_added: '2.7'
  max_attempts:
    description:
      - Retry attempts on network issues and reaching API limits
    default: 5
    required: false
    version_added: '2.7'

author:
  - Lester Wade (@lwade)
  - Paul Arthur (@flowerysong)
extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
- name: Ensure tags are present on a resource
  ec2_tag:
    region: eu-west-1
    resource: vol-XXXXXX
    state: present
    tags:
      Name: ubervol
      env: prod

- name: Ensure all volumes are tagged
  ec2_tag:
    region:  eu-west-1
    resource: '{{ item.id }}'
    state: present
    tags:
      Name: dbserver
      Env: production
  with_items: '{{ ec2_vol.volumes }}'

- name: Retrieve all tags on an instance
  ec2_tag:
    region: eu-west-1
    resource: i-xxxxxxxxxxxxxxxxx
    state: list
  register: ec2_tags

- name: Remove all tags except for Name from an instance
  ec2_tag:
    region: eu-west-1
    resource: i-xxxxxxxxxxxxxxxxx
    tags:
        Name: ''
    state: absent
    purge_tags: true
'''

RETURN = '''
tags:
  description: A dict containing the tags on the resource
  returned: always
  type: dict
added_tags:
  description: A dict of tags that were added to the resource
  returned: If tags were added
  type: dict
removed_tags:
  description: A dict of tags that were removed from the resource
  returned: If tags were removed
  type: dict
'''

from ansible.module_utils.aws.core import AnsibleAWSModule
from ansible.module_utils.ec2 import boto3_tag_list_to_ansible_dict, ansible_dict_to_boto3_tag_list, compare_aws_tags

try:
    from botocore.exceptions import BotoCoreError, ClientError
except:
    pass    # Handled by AnsibleAWSModule


def get_tags(ec2, module, resource):
    filters = [{'Name': 'resource-id', 'Values': [resource]}]
    try:
        return boto3_tag_list_to_ansible_dict(ec2.describe_tags(Filters=filters)['Tags'])
    except (BotoCoreError, ClientError) as e:
        module.fail_json_aws(e, msg='Failed to fetch tags for resource {0}'.format(resource))


def main():
    argument_spec = dict(
        resource=dict(required=True),
        tags=dict(type='dict'),
        purge_tags=dict(type='bool', default=False),
        state=dict(default='present', choices=['present', 'absent', 'list']),
        max_attempts=dict(type='int',required=False, default=5),
    )
    required_if = [('state', 'present', ['tags']), ('state', 'absent', ['tags'])]

    module = AnsibleAWSModule(argument_spec=argument_spec, required_if=required_if, supports_check_mode=True)

    resource = module.params['resource']
    tags = module.params['tags']
    state = module.params['state']
    purge_tags = module.params['purge_tags']
    max_attempts = module.params.get('max_attempts')

    result = {'changed': False}
#    region, ec2_url, aws_connect_params = get_aws_connection_info(module, boto3=True)
#
#    if aws_connect_params.get('config'):
#      config = aws_connect_params.get('config')
#      config.retries = {'max_attempts': max_attempts}
#    else:
#      config = botocore.config.Config(
#        retries={'max_attempts': max_attempts},
#      )
#      aws_connect_params['config'] = config
#
#    if region:
#        try:
#            ec2 = boto3_conn(
#                module,
#                conn_type='client',
#                resource='ec2',
#                region=region,
#                endpoint=ec2_url,
#                **aws_connect_params
#            )
#        except (botocore.exceptions.ProfileNotFound, Exception) as e:
#            module.fail_json(msg=to_native(e), exception=traceback.format_exc())
#    else:
#        module.fail_json(msg="region must be specified")

    ec2 = module.client('ec2')
    # We need a comparison here so that we can accurately report back changed status.
    # Need to expand the gettags return format and compare with "tags" and then tag or detag as appropriate.
    filters = {'resource-id': resource}
    gettags = ec2.describe_tags(Filters=ansible_dict_to_boto3_filter_list(filters))["Tags"]

    current_tags = get_tags(ec2, module, resource)
#    dictadd = {}
#    dictremove = {}
#    baddict = {}
#    tagdict = {}
#    result = {}
    
#    for tag in gettags:
#    tagdict[tag["Key"]] = tag["Value"]

    if state == 'list':
        module.exit_json(changed=False, tags=current_tags)
#    if state == 'present':
#        if not tags:
#            module.fail_json(msg="tags argument is required when state is present")
#        if set(tags.items()).issubset(set(tagdict.items())):
#            module.exit_json(msg="Tags already exists in %s." % resource, changed=False)
#        else:
#            for (key, value) in set(tags.items()):
#                if (key, value) not in set(tagdict.items()):
#                    dictadd[key] = value
#        if not module.check_mode:
#            ec2.create_tags(Resources=[resource], Tags=[{"Key": k, "Value": v} for k,v in dictadd.iteritems()])
#        result["changed"] = True
#        result["msg"] = "Tags %s created for resource %s." % (dictadd, resource)

    add_tags, remove = compare_aws_tags(current_tags, tags, purge_tags=purge_tags)

    remove_tags = {}
    if state == 'absent':
        for key in tags:
            if key in current_tags and current_tags[key] == tags[key]:
                remove_tags[key] = tags[key]

    for key in remove:
        remove_tags[key] = current_tags[key]

    if remove_tags:
        result['changed'] = True
        result['removed_tags'] = remove_tags
#    elif state == 'absent':
#        if not tags:
#            module.fail_json(msg="tags argument is required when state is absent")
#        for (key, value) in set(tags.items()):
#            if (key, value) not in set(tagdict.items()):
#                baddict[key] = value
#                if set(baddict) == set(tags):
#                    module.exit_json(msg="Nothing to remove here. Move along.", changed=False)
#        for (key, value) in set(tags.items()):
#            if (key, value) in set(tagdict.items()):
#                dictremove[key] = value
        if not module.check_mode:
            try:
                ec2.delete_tags(Resources=[resource], Tags=ansible_dict_to_boto3_tag_list(remove_tags))
            except (BotoCoreError, ClientError) as e:
                module.fail_json_aws(e, msg='Failed to remove tags {0} from resource {1}'.format(remove_tags, resource))
#            ec2.delete_tags(Resources=[resource], Tags=[{"Key": k, "Value": v} for k,v in dictremove.iteritems()])
#        result["changed"] = True
#        result["msg"] = "Tags %s removed for resource %s." % (dictremove, resource)

    if state == 'present' and add_tags:
        result['changed'] = True
        result['added_tags'] = add_tags
        current_tags.update(add_tags)
        if not module.check_mode:
            try:
                ec2.create_tags(Resources=[resource], Tags=ansible_dict_to_boto3_tag_list(add_tags))
            except (BotoCoreError, ClientError) as e:
                module.fail_json_aws(e, msg='Failed to set tags {0} on resource {1}'.format(add_tags, resource))
#    elif state == 'list':
#        result["changed"] = False
#        result["tags"] = tagdict
#
#    if module._diff:
#      newdict = dict(tagdict)
#      for key, value in dictadd.iteritems():
#        newdict[key] = value
#      for key in dictremove.iterkeys():
#        newdict.pop(key, None)
#      result['diff'] = {
#        'before': "\n".join(["%s: %s" % (key, value) for key, value in tagdict.iteritems()]) + "\n",
#        'after':  "\n".join(["%s: %s" % (key, value) for key, value in newdict.iteritems()]) + "\n"
#      }
#    module.exit_json(**result)

    result['tags'] = get_tags(ec2, module, resource)
    module.exit_json(**result)


if __name__ == '__main__':
    main()
