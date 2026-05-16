from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from marketplace.models import IndustrialProduct


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return ['home']

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return IndustrialProduct.objects.all()

    def location(self, obj):
        return f"/producto/{obj.id}/"
