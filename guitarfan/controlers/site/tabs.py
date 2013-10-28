#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math

from flask import render_template, request, redirect, url_for, flash, Blueprint, jsonify, current_app
from sqlalchemy import func, or_

from guitarfan.models import *
from guitarfan.extensions.flasksqlalchemy import db


bp_site_tabs = Blueprint('bp_site_tabs', __name__, template_folder="../../templates/site")


@bp_site_tabs.route('/tabs')
@bp_site_tabs.route('/tabs/<int:page>')
def tabs(page = 1):
    if 'artist' in request.args:
        artist_id = request.args['artist']
        artist = Artist.query.get(artist_id)
        tabs = Tab.query.filter(Tab.artist_id == artist_id).order_by('update_time desc').paginate(page, current_app.config['TABS_PER_PAGE'], True)
        return render_template('tabs.html', tabs=tabs, artist=artist, mode='artist')
    elif 'style' in request.args:
        style_id = int(request.args['style'])
        style = enums.MusicStyle.get_item_text(style_id)
        tabs = Tab.query.filter(Tab.style_id == style_id).order_by('update_time desc').paginate(page, current_app.config['TABS_PER_PAGE'], True)
        return render_template('tabs.html', tabs=tabs, style=style, mode='style')
    elif 'tag' in request.args:
        tag_id = request.args['tag']
        tag = Tag.query.get(tag_id)
        tabs = Tab.query.join(Tab.tags).filter(Tag.id == tag_id).order_by('Tab.update_time desc').paginate(page, current_app.config['TABS_PER_PAGE'], True)
        return render_template('tabs.html', tabs=tabs, tag=tag, mode='tag')
    # TODO search mode
    #elif 'search' in request.args:
    #    return render_template('tabs.html', tabs=tabs, tag=tag, mode='search')
    else:
        letters = map(chr, range(65, 91))
        letters.append('0-9')
        letters.append('Other')
        regions = ArtistRegion.get_described_items()
        categories = ArtistCategory.get_described_items()

        order_by = 'update_time'
        if 'order' in request.args and request.args['order'] == 'hot':
            order_by = 'hits'

        tabs = Tab.query.order_by(order_by + ' desc').paginate(page, current_app.config['TABS_PER_PAGE'], True)
        return render_template('tabs.html', letters=letters, regions=regions, categories=categories, tabs=tabs, mode='list')


@bp_site_tabs.route('/artists.json', methods=['POST'])
def artists_json():
    letter = request.form['queryFilter[artistLetter]']
    category_id = int(request.form['queryFilter[artistCategoryId]'])
    region_id = int(request.form['queryFilter[artistRegionId]'])
    artists = []
    for id, name, category in db.session.query(Artist.id, Artist.name, Artist.category_id) \
        .filter(or_(Artist.letter == letter)) \
        .filter(or_(category_id == 0, Artist.category_id == category_id)) \
        .filter(or_(region_id == 0, Artist.region_id == region_id)) \
        .order_by('category_id'):
        artists.append({'id': id, 'name': name, 'category': category})
    return jsonify(artists=artists)


@bp_site_tabs.route('/tabs.json', methods=['POST'])
def tabs_json():
    letter = request.form['queryFilter[artistLetter]']
    category_id = int(request.form['queryFilter[artistCategoryId]'])
    region_id = int(request.form['queryFilter[artistRegionId]'])
    order_by = 'Tab.update_time' if request.form['queryFilter[orderBy]'] == 'time' else 'Tab.hits'
    artists = request.form['queryFilter[artistIds]'].split('|') if request.form['queryFilter[artistIds]'] != '' else []
    page_index = int(request.form['queryFilter[pageIndex]'])
    tabs = []

    page_size = current_app.config['TABS_PER_PAGE']

    count = db.session.query(func.count(Tab.id)).join(Artist) \
        .filter(or_(letter == 'All', Artist.letter == letter)) \
        .filter(or_(category_id == 0, Artist.category_id == category_id)) \
        .filter(or_(region_id == 0, Artist.region_id == region_id)) \
        .filter(or_(len(artists) == 0, Artist.id.in_(artists))).scalar()

    page_count = math.ceil(float(count)/page_size)

    tabQuery = db.session.query(Tab.title, Tab.style_id, Tab.difficulty_id, Tab.hits, Tab.artist_id, Artist.name).join(Artist) \
        .filter(or_(letter == 'All', Artist.letter == letter)) \
        .filter(or_(category_id == 0, Artist.category_id == category_id)) \
        .filter(or_(region_id == 0, Artist.region_id == region_id)) \
        .filter(or_(len(artists) == 0, Artist.id.in_(artists))) \
        .order_by(order_by + ' desc').limit(page_size).offset(page_size * (page_index - 1))

    for title, styleId, difficaltyId, hits, artistId, artistName in tabQuery:
        tabs.append({
            'title': title,
            'style': MusicStyle.get_item_text(styleId),
            'difficalty': DifficultyDegree.get_item_text(difficaltyId),
            'hits': hits,
            'artistId': artistId,
            'artistName': artistName
        })

    return jsonify(tabs=tabs, pageIndex=page_index, pageCount=page_count)