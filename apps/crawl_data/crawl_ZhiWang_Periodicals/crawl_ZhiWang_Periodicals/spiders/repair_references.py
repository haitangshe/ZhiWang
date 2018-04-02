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
from .SelectData import select_references


class RepairReferencesSpider(scrapy.Spider):
    _re_filename = re.compile('filename=((.*?))&')
    name = 'repair_references'
    header = {
        'Host': 'kns.cnki.net',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
    }
    start_urls = ['http://kns.cnki.net/']

    def start_requests(self):
        """
        控制开始
        从数据库中找出所有的引用均为空的参考文献id
        """
        references = References.objects.filter(CJFQ='', CDFD='', CMFD='', CBBD='', SSJD='', CRLDENG='', CCND='',
                                               CPFD='')  # 找到全是空白的数据
        details = Detail.objects.filter(references__in=references)
        # details = Detail.objects.filter(references=None)
        print(details.count())
        count = 1
        for detail in details:
            print(count)
            count += 1
            references_url = \
                'http://kns.cnki.net/kcms/detail/frame/list.aspx?dbcode=CJFQ&filename={0}&RefType=1&page=1' \
                    .format(detail.detail_id)
            yield scrapy.Request(url=references_url, headers=self.header, callback=self.parse,
                                 meta={'detail': detail, 'cur_page': 1, 'CJFQ_list': [], 'CDFD_list': [],
                                       'CMFD_list': [], 'CBBD_list': [], 'SSJD_list': [], 'CRLDENG_list': [],
                                       'CCND_list': [], 'CPFD_list': []})

    def parse(self, response):
        detail = response.meta.get('detail')
        cur_page = response.meta.get('cur_page')
        references_url = response.url.split('page=')[0] + 'page=' + str(cur_page + 1)
        pc_CJFQ = int(response.xpath('//span[@id="pc_CJFQ"]/text()').extract_first(default=0))
        CJFQ_list = response.meta.get('CJFQ_list')
        pc_CDFD = int(response.xpath('//span[@id="pc_CJFQ"]/text()').extract_first(default=0))
        CDFD_list = response.meta.get('CDFD_list')
        pc_CMFD = int(response.xpath('//span[@id="pc_CMFD"]/text()').extract_first(default=0))
        CMFD_list = response.meta.get('CMFD_list')
        pc_CBBD = int(response.xpath('//span[@id="pc_CBBD"]/text()').extract_first(default=0))
        CBBD_list = response.meta.get('CBBD_list')
        pc_SSJD = int(response.xpath('//span[@id="pc_SSJD"]/text()').extract_first(default=0))
        SSJD_list = response.meta.get('SSJD_list')
        pc_CRLDENG = int(response.xpath('//span[@id="pc_CRLDENG"]/text()').extract_first(default=0))
        CRLDENG_list = response.meta.get('CRLDENG_list')
        pc_CCND = int(response.xpath('//span[@id="pc_CCND"]/text()').extract_first(default=0))
        CCND_list = response.meta.get('CCND_list')
        pc_CPFD = int(response.xpath('//span[@id="pc_CPFD"]/text()').extract_first(default=0))
        CPFD_list = response.meta.get('CPFD_list')
        page = max(pc_CJFQ, pc_CDFD, pc_CMFD, pc_CBBD, pc_SSJD, pc_CRLDENG, pc_CCND, pc_CPFD)  # 找到最大的参考文献库个数，定制翻页次数
        page = (page / 10)  # 每页有10条数据

        select_references(response,
                          CJFQ_list, CDFD_list, CMFD_list, CBBD_list, SSJD_list, CRLDENG_list, CCND_list, CPFD_list)

        if page > cur_page:
            # 网页+1继续获取信息
            yield scrapy.Request(url=references_url, headers=self.header, callback=self.parse,
                                 meta={'detail': detail, 'cur_page': cur_page + 1,
                                       'CJFQ_list': CJFQ_list, 'CDFD_list': CDFD_list, 'CMFD_list': CMFD_list,
                                       'CBBD_list': CBBD_list, 'SSJD_list': SSJD_list, 'CRLDENG_list': CRLDENG_list,
                                       'CCND_list': CCND_list, 'CPFD_list': CPFD_list})
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

            if len(
                    CJFQ_list + CDFD_list + CMFD_list + CBBD_list + SSJD_list + CRLDENG_list + CCND_list + CPFD_list) == 0:
                detail.references = References.objects.filter(id=76438)[0]
            else:
                if detail.references.id == 76438:
                    references = References()
                    references.CJFQ = ' '.join(CJFQ_list)
                    references.CDFD = ' '.join(CDFD_list)
                    references.CMFD = ' '.join(CMFD_list)
                    references.CBBD = ' '.join(CBBD_list)
                    references.SSJD = ' '.join(SSJD_list)
                    references.CRLDENG = ' '.join(CRLDENG_list)
                    references.CCND = ' '.join(CCND_list)
                    references.CJFQ = ' '.join(CJFQ_list)
                    references.save()
                    detail.references = references
                else:
                    detail.references.CJFQ = ' '.join(CJFQ_list)
                    detail.references.CDFD = ' '.join(CDFD_list)
                    detail.references.CMFD = ' '.join(CMFD_list)
                    detail.references.CBBD = ' '.join(CBBD_list)
                    detail.references.SSJD = ' '.join(SSJD_list)
                    detail.references.CRLDENG = ' '.join(CRLDENG_list)
                    detail.references.CCND = ' '.join(CCND_list)
                    detail.references.CJFQ = ' '.join(CJFQ_list)
                    detail.references.save()
            detail.save()
