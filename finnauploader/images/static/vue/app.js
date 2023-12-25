function init_vue() {
   function deleteclick(index)
   {
       alert('deleteclick');
   }

   function uploadclick(index)
   {
       alert('uploadclick');
   }


   Vue.component('photos-component', {
      template: '#photos-template',
      props: ['photos'],
      methods: {
         deleteclick: deleteclick,
         uploadclick: uploadclick,
      }
   });


}

new Vue({
    el: '#app',
    data: {
        message: 'Loading...',
        params: {}, // placeholder
        modal: {}, // placeholder
        photos: [ { 'title':'title', 'year':1234, 'finna_id':'albumitauki.0AIOzSF80pOU'}]
    },
    mounted() {
        fetch('/api/hello/')
            .then(response => response.json())
            .then(data => {
                this.message = data.message;
            });
        fetch('/finna/')
            .then(response => response.json())
            .then(data => {
                this.photos = data;
            });

    }
});

$(init_vue);
