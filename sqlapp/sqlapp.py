from django.db import models, connection
from django.forms import ModelForm, Textarea
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.apps import apps
import csv


class SQL(models.Model):

    query = models.TextField('Query')
    formatting = models.BooleanField(
        'Format', blank=True, default=False)
    download_csv = models.BooleanField(
        'Download CSV', blank=True, default=False)

    class Meta:
        managed = False
        verbose_name = 'SQL'
        verbose_name_plural = 'SQL'


class SQLForm(ModelForm):

    class Meta:
        model = SQL
        fields = '__all__'
        widgets = {
            'query': Textarea(attrs={
                'id': 'query',
                'autofocus': True
            })
        }


@staff_member_required
def execute_sql(request):

    context = {}
    context['table_names'] = get_table_names()

    if request.method == 'POST':
        request.POST = request.POST.copy()
        form = SQLForm(request.POST)
        form.is_valid()
        query = form.cleaned_data['query']

        if form.cleaned_data['formatting']:
            query = format_sql(query)
            form.data['query'] = query

        with connection.cursor() as cursor:
            try:
                cursor.execute(query)
            except Exception as error:
                context['info'] = error
            else:
                if cursor.description:
                    context['header'] = [error[0] for error
                                         in cursor.description]
                    context['rows'] = cursor.fetchall()
                else:
                    context['info'] = 'No result'
        if form.cleaned_data['download_csv']:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="sql.csv"'

            writer = csv.writer(response)
            writer.writerow(context['header'])
            for row in context['rows']:
                writer.writerow(row)
            return response

    else:
        form = SQLForm()

    context['form'] = form
    context['title'] = "SQL"

    return render(request, 'sqlapp/sqlapp.html', context)


def format_sql(query):
    keywords = ['select', 'from', 'as', 'join', 'left', 'on',
                'where', 'and', 'case', 'else', 'end', 'is',
                'null', 'union', 'order', 'by', 'concat',
                'to_char', 'limit', 'or']
    new_query = []
    flag = False

    for word in query.split():
        if word in keywords:
            word = word.upper()

        word += ' '
        if '(' in word and ')' not in word:
            flag = True
            new_query.append(word)
            continue
        if flag and (')' not in word or '(' in word):
            new_query.append(word)
            continue
        else:
            flag = False

        if word.strip().endswith(','):
            word += '\n\t'
        if word.strip() == 'FROM':
            word = '\n' + word
        if word.strip() == 'WHERE':
            word = '\n' + word + '\n\t'
        if word.strip() in ('LEFT', 'AND'):
            word = '\n\t' + word
        if word.strip() == 'SELECT':
            word += '\n\t'
        if word.strip() in ('WHEN', 'ELSE', 'END'):
            word = '\n\t\t' + word

        new_query.append(word)

    return ''.join(new_query)


def get_table_names():
    tables = []
    for app_name, app in apps.app_configs.items():
        for model in app.get_models():
            tables.append(model._meta.db_table)
    tables = [name for name in tables if not name.startswith('django')]
    tables.sort()
    return tables
