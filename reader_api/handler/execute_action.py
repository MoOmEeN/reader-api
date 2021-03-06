#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import traceback
import os
from os.path import join as pth_join

import requests
import jwt
from jinja2 import Template

import reader_api.config as config
from reader_api.logging_utils import get_logger
from reader_api import token_generator
from reader_api.handler.constants import OPERATION, TITLE, ARTICLE_ID, USER_ID, \
    MARK_AS_READ, MARK_AS_UNREAD, SAVE_ARTICLE
from reader_api.config import ACTION_PARAM, SELF_URL

logger = get_logger(__name__)

API_URL = 'https://m1ndoce0cl.execute-api.eu-west-1.amazonaws.com/v1'

TOKEN_EXPIRATION_TIME = 2


def handle(event):
    global CLIENT_ID, CLIENT_SECRET, TOKEN_SECRET
    CLIENT_ID = config.get('feeds_client_id')
    CLIENT_SECRET = config.get('feeds_client_secret')
    TOKEN_SECRET = config.get('token_secret')

    try:
        try:
            token = event['queryStringParameters'][ACTION_PARAM]
            payload = token_generator.decode(token)
            if payload[OPERATION] == MARK_AS_READ:
                logger.info('Mark read request', extra={'event': 'mark-read'})
                mark_read(user_id=payload[USER_ID],
                          article_id=payload[ARTICLE_ID])
                return render_template('marked-read.html', title=payload[TITLE], unread_link=generate_new_link(payload, MARK_AS_UNREAD))
            elif payload[OPERATION] == MARK_AS_UNREAD:
                logger.info('Keep unread request', extra={
                            'event': 'keep-unread'})
                keep_unread(user_id=payload[USER_ID],
                            article_id=payload[ARTICLE_ID])
                return render_template('marked-unread.html', title=payload[TITLE], read_link=generate_new_link(payload, MARK_AS_READ))
            elif payload[OPERATION] == SAVE_ARTICLE:
                logger.info('Save article request', extra={
                            'event': 'save-article'})
                save_article(user_id=payload[USER_ID],
                             article_id=payload[ARTICLE_ID])
                return render_template('save-article.html', title=payload[TITLE])
            else:
                return render_template('error.html')

        except jwt.ExpiredSignatureError:
            logger.info('Token expired', extra={'event': 'expired'})
            return render_template('token-expired.html', expiration=TOKEN_EXPIRATION_TIME)
    except Exception, e:
        print(traceback.format_exc())
        logger.info('Error', extra={'event': 'error'})
        return render_template('error.html')


def mark_read(article_id, user_id):
    user_token = authenticate_user(user_id)
    if user_token is None:
        return

    request = [
        article_id
    ]

    r = requests.post(API_URL + "/feeds/markArticleRead",
                      data=json.dumps(request),
                      headers={
                          'Authorization': user_token,
                          'Content-Type': 'application/json'
                      })
    if r.status_code != requests.codes.ok:
        logger.info('Mark read error', extra={'event': 'mark-read-error'})
        print 'Error trying to mark as read: {}, response: {}'.format(r.status_code, r.text)
        raise Exception('Error')


def keep_unread(article_id, user_id):
    user_token = authenticate_user(user_id)
    if user_token is None:
        return

    request = [
        article_id
    ]

    r = requests.post(API_URL + "/feeds/markArticleUnread",
                      data=json.dumps(request),
                      headers={
                          'Authorization': user_token,
                          'Content-Type': 'application/json'
                      })
    if r.status_code != requests.codes.ok:
        logger.info('Keep unread error', extra={'event': 'keep-unread-error'})
        print 'Error trying to mark as not read: {}, response: {}'.format(r.status_code, r.text)
        raise Exception('Error')


def save_article(article_id, user_id):
    user_token = authenticate_user(user_id)
    if user_token is None:
        return

    request = [
        article_id
    ]

    r = requests.post(API_URL + "/feeds/saveArticle",
                      data=json.dumps(request),
                      headers={
                          'Authorization': user_token,
                          'Content-Type': 'application/json'
                      })
    if r.status_code != requests.codes.ok:
        logger.info('Save article error', extra={
                    'event': 'save-article-error'})
        print 'Error trying to save article: {}, response: {}'.format(r.status_code, r.text)
        raise Exception('Error')


def authenticate_user(user_id):
    request = {
        'grant_type': 'bearer',
        'client_id': CLIENT_ID,
        'token': generate_user_token(user_id)
    }
    r = requests.post(API_URL + "/login",
                      data=json.dumps(request),
                      headers={
                          'Content-Type': 'application/json'
                      })
    if r.status_code == requests.codes.ok:
        return r.content
    else:
        print 'Error trying to authenticate: {}, response: {}'.format(r.status_code, r.text)
        raise Exception('Couldnt authenticate')


def generate_user_token(user_id):
    payload = {
        'userId': int(user_id)
    }
    return jwt.encode(payload, CLIENT_SECRET, algorithm='HS256')


def render_template(template_file, **kwargs):
    with open(pth_join(os.path.dirname(__file__), '..', '..', 'templates', template_file), 'r') as f:
        template = Template(f.read())
        content = template.render(kwargs)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html; charset=utf-8'
            },
            'body': content
        }


def generate_new_link(current_payload, new_operation):
    current_payload[OPERATION] = new_operation
    token = token_generator.encode(current_payload)
    return SELF_URL + token
