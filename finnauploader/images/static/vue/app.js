function init_vue() {
   function getSearchParams(k, d){
      var p={};
      location.search.replace(/[?&]+([^=&]+)=([^&]*)/gi,function(s,k,v){p[k]=v})
      var ret= k?p[k]:p;
      if (typeof(ret)==="undefined") return d;
      else return ret;
   }

   function randomclick(limit)
   {
      var search=$("input[name='searchkey']").val();
      url='';
      delim = '?';
      if (limit!=10) {
          url+=delim + 'limit=' + limit;
          delim='&';
      }
      if (search!='') {
          url+=delim + 'searchkey=' +  encodeURIComponent(search);
      }
      document.location=url;
   }

   function deleteclick(index)
   {
      var p=this.photos[index];
      var url='/api/finna/' + p.id + '/skip';
//      if (typeof(p.marker) !== "undefined") p.marker.remove();
      $.getJSON(url, function (json) {});
      this.photos.splice(index,1);
   }

   function uploadclick(index)
   {
      var p=this.photos[index];
      var url='/api/finna/' + p.id + '/upload';
//      if (typeof(p.marker) !== "undefined") p.marker.remove();
      $.getJSON(url, function (json) {
          rows.push(json.filename.toString())
          app.logrows=rows
      });
      this.photos.splice(index,1);
   }


   Vue.component('topbar-component', {
      template: '#topbar-template',
      props: ['params'],
      methods: {
         'random': randomclick
      }
   });

   Vue.component('logging-component', {
      template: '#logging-template',
      props: ['logrows'],
   });


   Vue.component('photos-component', {
      template: '#photos-template',
      props: ['photos'],
      methods: {
         deleteclick: deleteclick,
         uploadclick: uploadclick,
      }
   });

 var limit=parseInt(decodeURIComponent(getSearchParams('limit',15)));
 var searchkey=decodeURIComponent(getSearchParams('searchkey', "").replace(/\+/g, '%20'));

 var rows=[]
 var app = new Vue({
    el: '#app',
    data: {
        message: 'Loading...',
        params:{
            searchkey:searchkey,
            limit:limit,
            submitted: 0,
            confirmed: 0
        },
        modal: {}, // placeholder
        photos: [ { 'title':'title', 'year':1234, 'finna_id':'albumitauki.0AIOzSF80pOU', 'subjects':[], 'summaries':[]}],
        logrows: []
    },
    mounted() {
        fetch('/api/hello/')
            .then(response => response.json())
            .then(data => {
                this.message = data.message;
            });

        var random_url='/api/finna/random'

        delim = '?'
        if (this.params.limit!=15) {
            random_url+=delim + 'limit=' + this.params.limit;
            delim = '&'
        }
        if (searchkey!='') {
            random_url+=delim + 'searchkey=' +  encodeURIComponent(searchkey);
            delim = '&'
        }

        fetch(random_url)
            .then(response => response.json())
            .then(data => {
                this.photos = data;
            });

    }
});
}

$(init_vue);
