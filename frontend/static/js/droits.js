// Page « Droits » : la case d'un bloc coche ou décoche toutes ses fonctions pour ce profil,
// et s'affiche à moitié cochée quand seules certaines fonctions le sont.
(function () {
  "use strict";

  function casesDesFonctions(bloc, profil) {
    return bloc.querySelectorAll(".ligne-fonction input[data-profil='" + profil + "']");
  }

  function mettreAJourCaseBloc(bloc, caseBloc) {
    var cases = Array.prototype.slice.call(casesDesFonctions(bloc, caseBloc.dataset.profil));
    var nombreCochees = cases.filter(function (caseFonction) { return caseFonction.checked; }).length;
    caseBloc.checked = nombreCochees === cases.length;
    caseBloc.indeterminate = nombreCochees > 0 && nombreCochees < cases.length;
  }

  document.querySelectorAll(".tableau-droits tbody[data-bloc]").forEach(function (bloc) {
    bloc.querySelectorAll("input[data-case-bloc]").forEach(function (caseBloc) {
      mettreAJourCaseBloc(bloc, caseBloc);
      caseBloc.addEventListener("change", function () {
        casesDesFonctions(bloc, caseBloc.dataset.profil).forEach(function (caseFonction) {
          caseFonction.checked = caseBloc.checked;
        });
        caseBloc.indeterminate = false;
      });
    });
    bloc.querySelectorAll(".ligne-fonction input").forEach(function (caseFonction) {
      caseFonction.addEventListener("change", function () {
        mettreAJourCaseBloc(bloc, bloc.querySelector("input[data-case-bloc][data-profil='" + caseFonction.dataset.profil + "']"));
      });
    });
  });
})();
