# -*- coding: utf-8 -*-
import scrapy
from django.db.models import Q  # 数据库中用多操作
import re

from crawl_data.models import Summary, Periodicals, Detail
from crawl_data.crawl_ZhiWang_Periodicals.crawl_ZhiWang_Periodicals.items import DetailItem, ReferencesCJFQItem, \
    ReferencesCMFDItem, ReferencesCDFDItem, ReferencesCBBDItem, \
    ReferencesSSJDItem, ReferencesCRLDENGItem, ReferencesItem, ReferencesCCNDItem, ReferencesCPFDItem
from crawl_data.models import ReferencesCJFQ, ReferencesCMFD, ReferencesCDFD, ReferencesCBBD, ReferencesSSJD, \
    ReferencesCRLDENG, References, ReferencesCCND, ReferencesCPFD
from .SelectData import select_detail, select_references
from settings import REFERENCES_DBNAME


class IncrementalCrawlDetailSpider(scrapy.Spider):
    _re_filename = re.compile('filename=((.*?))&')
    name = 'incremental_crawl_detail'
    start_urls = ['http://http://kns.cnki.net//']
    header = {
        'Host': 'kns.cnki.net',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
    }

    def start_requests(self):
        summarys = Summary.objects.filter(have_detail=False, source__mark=True)  # 标记的期刊且在做增量summary时候处理过的
        all_count = summarys.count()
        count = 0
        for summary in summarys:
            print(count, '/', all_count)
            count += 1
            yield scrapy.Request(url=summary.url, headers=self.header, callback=self.parse,
                                 meta={'summary': summary})

    def parse(self, response):
        summary = response.meta.get('summary')
        paper_id, keywords, abstract, date, authors_dic, orgs_dic = select_detail(response=response)
        detail_item = DetailItem()
        detail_item['detail_id'] = paper_id
        detail_item['detail_keywords'] = keywords
        detail_item['detail_abstract'] = abstract
        detail_item['detail_date'] = date
        detail_item['authors_dic'] = authors_dic
        detail_item['organizations_dic'] = orgs_dic
        detail_item['summary'] = summary
        yield detail_item
        detail = Detail.objects.get(id=detail_item['database_id'])
        if detail.references is None:
            references_url = 'http://kns.cnki.net/kcms/detail/frame/list.aspx?dbcode=CJFQ&filename={0}&RefType=1&page=1' \
                .format(detail.detail_id)
            references_list_dict = dict()
            for references_name in REFERENCES_DBNAME:
                references_list_dict[references_name + '_list'] = []
            yield scrapy.Request(url=references_url, headers=self.header, callback=self.parse_references,
                                 meta={'detail': detail, 'cur_page': 1, 'references_list_dict': references_list_dict})

    def parse_references(self, response):
        detail = response.meta.get('detail')
        cur_page = response.meta.get('cur_page')
        references_url = response.url.split('page=')[0] + 'page=' + str(cur_page + 1)
        every_page = []  # 每种引用期刊的数量
        references_list_dict = response.meta.get('references_list_dict')
        for references_name in REFERENCES_DBNAME:
            every_page.append(
                int(response.xpath('//span[@id="pc_{}"]/text()'.format(references_name)).extract_first(default=0))
            )

        page = max(every_page)  # 找到最大的参考文献库个数，定制翻页次数
        page = (page / 10)  # 每页有10条数据

        for item in select_references(response, **references_list_dict):
            yield item

        if page > cur_page:
            # 网页+1继续获取信息
            yield scrapy.Request(url=references_url, headers=self.header, callback=self.parse_references,
                                 meta={'detail': detail, 'cur_page': cur_page + 1,
                                       'references_list_dict': references_list_dict})
        else:
            # # Debug
            # print('CJFQ_list:', CJFQ_list)
            # print('CDFD_list:', CDFD_list)
            # print('CMFD_list:', CMFD_list)
            # print('CBBD_list:', CBBD_list)
            # print('SSJD_list:', SSJD_list)
            # print('CRLDENG_list:', CRLDENG_list)
            # print('CCND_list:', CCND_list)
            # print('CPFD_list:', CPFD_list)

            if sum(len(x) for x in references_list_dict.values()) == 0:
                references = References.objects.filter(id=76438)[0]
            else:
                references = References()
                for references_name in REFERENCES_DBNAME:
                    references.__setattr__(references_name, ' '.join(references_list_dict[references_name + '_list']))
                references.save()
            detail.references = references
            detail.save()
