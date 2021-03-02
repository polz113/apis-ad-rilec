<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

use App\Http\Controllers\ApisHRMasterController;
use App\Http\Controllers\ApisOUController;
use App\Http\Controllers\ApisUserProfileController;
use App\Http\Controllers\LdapActionController;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
*/

Route::group(['middleware'=>'auth:api'], function(){
    /* Route::put('/replicate', 'ApisADController@update'); 
    Route::get('/replicate', 'ApisADController@list'); */
    Route::put('/hr/HRMaster/replicate', 'ApisHRMasterController@update');
    Route::get('/hr/HRMaster/replicate', 'ApisHRMasterController@list');
    /* Seznam uporabnikov v nekem trenutku */
    Route::get('/api/userprofile/', 'ApisUserProfileController@index');
    Route::get('/api/userprofile/{date}', 'ApisUserProfileController@index');
    /* Podatki o posamezniku v nekem trenutku */
    Route::get('/api/userprofile/{date}/{id}', 'ApisUserProfileController@show');
    /* Seznam org. enot v nekem trenutku */
    Route::get('/api/ou/{date}', [ApisOUController::class, 'index']);
    Route::get('/api/ou/', [ApisOUController::class, 'index']);
    /* Podrobnosti org. enote v nekem trenutku */
    Route::get('/api/ou/{date}/{uid}', 'ApisOUController@show');
    /* Drevo org. enot v nekem trenutku */
    Route::get('/api/outree/{date}', 'ApisOUController@tree_index');
    Route::get('/api/outree/', 'ApisOUController@tree_index');
    /* Drevo org. enot z uporabniki v nekem trenutku */
    Route::get('/api/usertree/{date}', 'ApisOUController@user_tree_index');
    Route::get('/api/usertree/', 'ApisOUController@user_tree_index');
    /* Skupine, v katerih je v nekem trenutku posameznik - morda spada v ApisOUController */
    Route::get('/api/usermemberof/{date}/{id}', 'ApisUserProfileController@memberof');
    /* Pripadniki skupine v nekem trenutku - morda spada v podrobnosti enote */
    Route::get('/api/oumembers/{date}/{uid}', 'ApisOUController@members');
    /* Seznam razporeditev po OE */
    Route::get('/api/groupassignment/{date}', 'GroupAssignmentController@index');
    Route::get('/api/groupassignment/', 'GroupAssignmentController@index');
    /* Podrobnosti prenosa podatkov v AD */
    /* Seznam podatkov za kopiranje v AD. Vključuje UserData in GroupAssignments. */
    Route::get('/api/dataset/', 'ADDatasetController@index');
    Route::get('/api/dataset/{id}', 'ADDatasetController@show');
    /* Ustvarjanje dataset-ov */
    Route::put('/api/dataset/{timestamp}', 'ADDatasetController@create');
    Route::put('/api/dataset/', 'ADDatasetController@create');
    /* Podrobnosti kopiranja v AD */
    Route::get('/api/ldapaction/{id}', 'LDAPActionController@id');
    /*
    Route::get('/user', function (Request $request) {
    return $request->user();
  }); */
});
